import json
import logging
from pathlib import Path
from typing import List, Tuple, Any

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine
from app.llm.context import apply_context_budget
from app.llm.parser import extract_yaml_from_text, parse_yaml_safely
from app.llm.providers.base import GenerateRequest

# Assuming default injection for simplicity in background tasks, we load active from store directly:
from app.config.store import ProviderConfigStore
from app.llm.provider_registry import build_default_provider_registry

logger = logging.getLogger(__name__)

def _get_active_provider():
    """Helper to fetch the configured active LLMProvider synchronously."""
    store = ProviderConfigStore("storage/provider_config.json")
    config = store.load()
    registry = build_default_provider_registry()
    provider = registry.get(config.active_provider)
    return provider

async def identify_abstractions(job: Job, engine: PipelineEngine) -> None:
    """
    Identify Abstractions LLM Node.
    Loads crawler context, budgets it, executes LLM prompt, and validates YAML extraction.
    """
    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    files_json = workspace_dir / "files.json"
    if not files_json.exists():
        raise FileNotFoundError(f"Crawler output files.json not found for job: {job.id}")
        
    files_data: List[Tuple[str, str]] = json.loads(files_json.read_text(encoding="utf-8"))
    
    # 1. Budget the context (max 100k globally, 10k per file)
    budgeted_files = apply_context_budget(files_data)
    file_count = len(budgeted_files)
    
    # 2. Build prompt context (Middle-out truncated snippets)
    context_builder = ""
    file_info = []
    
    for i, (path, content) in enumerate(budgeted_files):
        entry = f"--- File Index {i}: {path} ---\\n{content}\\n\\n"
        context_builder += entry
        file_info.append((i, path))

    file_listing_for_prompt = "\\n".join([f"- {idx} # {path}" for idx, path in file_info])
    
    prompt = f"""
For the project `{job.project_name}`:

Codebase Context:
{context_builder}

Analyze the codebase context.
Identify the top 5-10 core most important abstractions to help those new to the codebase.

For each abstraction, provide:
1. A concise `name`.
2. A beginner-friendly `description` explaining what it is with a simple analogy, in around 100 words.
3. A list of relevant `file_indices` (integers) using the format `idx # path/comment`.

List of file indices and paths present in the context:
{file_listing_for_prompt}

Format the output as a YAML list of dictionaries:

```yaml
- name: |
    Query Processing
  description: |
    Explains what the abstraction does.
    It's like a central dispatcher routing requests.
  file_indices:
    - 0 # path/to/file1.py
    - 3 # path/to/related.py
```"""
    
    # 3. Call LLM
    provider = _get_active_provider()
    response = provider.generate(GenerateRequest(prompt=prompt))
    
    # 4. Parse output
    yaml_str = extract_yaml_from_text(response.content)
    abstractions = parse_yaml_safely(yaml_str)
    
    if not isinstance(abstractions, list):
        raise ValueError("LLM Output for Identify Abstractions is not a valid list.")
        
    validated_abstractions = []
    for item in abstractions:
        if not isinstance(item, dict) or not all(k in item for k in ["name", "description", "file_indices"]):
            raise ValueError(f"Missing essential keys in abstraction item: {item}")
            
        validated_indices = []
        for idx_entry in item["file_indices"]:
            try:
                # LLM can sometimes return "0 # src/code.py" or just 0
                if isinstance(idx_entry, int):
                    idx = idx_entry
                else:
                    idx = int(str(idx_entry).split("#")[0].strip())
                    
                if not (0 <= idx < file_count):
                    raise ValueError(f"Invalid file index {idx} encountered in {item['name']}.")
                validated_indices.append(idx)
            except (ValueError, TypeError):
                continue # Graceful skip
                
        validated_abstractions.append({
            "name": item["name"],
            "description": item["description"],
            "files": sorted(list(set(validated_indices))),
        })

    logger.info(f"Job {job.id} identified {len(validated_abstractions)} abstractions.")
    
    # Finally, mutate Job state
    job.abstractions = {"items": validated_abstractions}
