import logging
from typing import List, Dict, Any
import asyncio
import os
import json
from pathlib import Path

from app.pipeline.models import Job, Chapter, JobStatus
from app.pipeline.engine import PipelineEngine
from app.llm.providers.base import GenerateRequest, LLMProvider

from app.config.store import ProviderConfigStore
from app.llm.provider_registry import build_default_provider_registry

logger = logging.getLogger(__name__)

def _get_active_provider() -> LLMProvider:
    store = ProviderConfigStore("storage/provider_config.json")
    config = store.load()
    registry = build_default_provider_registry()
    return registry.get(config.active_provider)

def _generate_chapter_sync(
    provider: LLMProvider,
    project_name: str,
    syllabus_item: Dict[str, Any],
    abstractions: List[Dict[str, Any]],
    relationships: Dict[str, Any],
    files_data: List[List[str]]  # filename, content pairs
) -> Chapter:
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
You are creating Chapter {chapter_num}: "{name}" for a tutorial about the project `{project_name}`.

Abstraction Summary:
{desc}

Relevant Code Context:
{file_context}

Overall Project Summary:
{relationships.get('summary', '')}

Write the full text for this chapter in Markdown. Make it engaging, educational, and easy to understand.
Explain what the abstraction stands for in the codebase and reference the provided code context. Do not include a broader project introduction unless it's necessary for this specific chapter. Just focus on explaining "{name}".
"""
    
    response = provider.generate(GenerateRequest(prompt=prompt))
    
    return Chapter(
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
        files_data = json.load(f)

    provider = _get_active_provider()
    abstractions = job.abstractions["items"]
    
    # Parallel generation
    tasks = []
    for item in job.syllabus:
        task = asyncio.to_thread(
            _generate_chapter_sync,
            provider,
            job.project_name,
            item,
            abstractions,
            job.relationships,
            files_data
        )
        tasks.append(task)
        
    chapters = await asyncio.gather(*tasks)
    
    # Sort them by chapter number just in case
    def sort_key(ch: Chapter) -> int:
        try:
            # simple parse "Chapter X:"
            return int(ch.title.split(":")[0].replace("Chapter ", ""))
        except:
            return 999
            
    chapters = sorted(chapters, key=sort_key)
    
    job.chapters = chapters
    logger.info(f"Job {job.id} generated {len(chapters)} chapters.")
