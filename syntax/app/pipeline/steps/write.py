import logging
from typing import List, Dict, Any, Tuple

from app.pipeline.models import Job, Chapter, JobStatus
from app.pipeline.engine import PipelineEngine
from app.llm.providers.base import GenerateRequest
from app.llm.cache import cached_generate, LLMProvider

logger = logging.getLogger(__name__)

def _get_active_provider(engine: PipelineEngine) -> LLMProvider:
    config = engine.config_store.load()
    provider = engine.provider_registry.get(config.active_provider, config.providers[config.active_provider])
    return provider

async def _generate_chapter(
    provider: LLMProvider,
    project_name: str,
    syllabus_item: Dict[str, Any],
    abstractions: List[Dict[str, Any]],
    relationships: Dict[str, Any],
    files_data: List[List[str]]  # filename, content pairs
) -> Tuple[int, Chapter]:
    """Synchronous function to call the LLM to write a single chapter."""
    idx = syllabus_item["abstraction_index"]
    abs_data = abstractions[idx]
    
    chapter_num = syllabus_item["chapter_number"]
    name = abs_data["name"]
    desc = abs_data.get("description", "No description.")
    
    # pull file contents relevant to this abstraction
    file_indices = abs_data.get("files", [])
    relevant_files = []
    for fidx in file_indices:
        if 0 <= fidx < len(files_data):
            fname, fcontent = files_data[fidx]
            relevant_files.append(f"--- File: {fname} ---\n{fcontent}\n")
    
    file_context = "\n".join(relevant_files)

    prompt = f"""
You are an expert technical writer and educator creating an engaging, story-driven tutorial for the codebase `{project_name}`.
You are currently writing **Chapter {chapter_num}: {name}**.

### Context Provided
**Abstraction Summary**: {desc}
**Overall Project Architecture Summary**: {relationships.get('summary', '')}

**Relevant Code Context** (Use this to understand the implementation, but avoid dumping large code blocks):
{file_context}

### Writing Guidelines
Your goal is to explain this technical concept to a beginner software engineer. You must NOT output a dry, jargon-filled technical document. You MUST output a highly engaging, story-like tutorial chapter that uses analogies.

**STRICT Formatting and Section Requirements**:
Make sure to include these specific sections in your Markdown output:

1. **Introduction Header**: Begin with a `# Chapter {chapter_num}: {name}` header.
2. **The Hook (Blockquote)**: Right under the header, write a welcoming blockquote (`>`) that hooks the reader, optionally connects to previous knowledge, and introduces what this abstraction basically is.
3. **"🤔 What Problem Does This Solve?"**: A section explaining the *why* before the *how*. Imagine a real-world, non-technical scenario where life is hard without this abstraction, and explain how this solves it.
4. **"🧩 How It Works (Simple Analogy)"**: A section containing a Markdown Table that explicitly maps the technical components of `{name}` to roles in your real-world analogy (e.g., Database -> The Pantry, API -> The Waiter).
5. **"✨ What It Does (In Plain English)"**: A numbered list breaking down the core responsibilities of `{name}` into 3 or 4 simple, digestible steps. Use plain English.
6. **"💻 Code Snapshot"**: Provide 1 (and only 1) small, beginner-friendly code snippet (max 10-15 lines) extracted or simplified from the `Relevant Code Context` that demonstrates the core idea. Explain it briefly.

**Tone constraints**: 
- Use emojis naturally to make it friendly. 
- Act like a patient, encouraging mentor. 
- Avoid heavy technical jargon where a simple word suffices.

Now, generate the Markdown content for Chapter {chapter_num}!
"""
    
    import asyncio
    import os
    import json
    from pathlib import Path
    
    response = await asyncio.to_thread(cached_generate, provider, GenerateRequest(prompt=prompt))
    
    return chapter_num, Chapter(
        title=f"Chapter {chapter_num}: {name}",
        description=desc,
        content=response.content.strip(),
        status=JobStatus.COMPLETED
    )


async def write_chapters(job: Job, engine: PipelineEngine) -> None:
    """
    Write Chapters Node.
    Parallelizes calls to the LLM to generate the content for each chapter defined in the syllabus.
    """
    if job.syllabus is None:
        logger.warning(f"Job {job.id} has syllabus=None. Skipping chapter generation.")
        job.chapters = []
        return
        
    if len(job.syllabus) == 0:
        logger.warning(f"Job {job.id} has empty syllabus. Skipping chapter generation.")
        job.chapters = []
        return

    if not job.abstractions or "items" not in job.abstractions:
        raise ValueError(f"Job {job.id} missing abstractions.")

    if not job.relationships:
        raise ValueError(f"Job {job.id} missing relationships.")

    # Read files data
    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    files_json_path = workspace_dir / "files.json"
    
    if not files_json_path.exists():
        raise FileNotFoundError(f"Missing files.json in {workspace_dir} for Job {job.id}")
        
    with open(files_json_path, "r", encoding="utf-8") as f:
        import json
        files_data = json.load(f)

    provider = _get_active_provider(engine)
    abstractions = job.abstractions["items"]
    
    import asyncio
    # Parallel generation
    tasks = []
    for item in job.syllabus:
        task = _generate_chapter(
            
            provider,
            job.project_name,
            item,
            abstractions,
            job.relationships,
            files_data
        )
        tasks.append(task)
        
    results = await asyncio.gather(*tasks)
    
    # Sort them by chapter number (the first element of the tuple)
    results = sorted(results, key=lambda x: x[0])
    chapters = [ch for _, ch in results]
    
    job.chapters = chapters
    logger.info(f"Job {job.id} generated {len(chapters)} chapters.")
