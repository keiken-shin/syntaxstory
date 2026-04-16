import asyncio
import json
import logging
from pathlib import Path
from typing import List, Tuple

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine
from app.llm.parser import extract_yaml_from_text, parse_yaml_safely
from app.llm.providers.base import GenerateRequest

logger = logging.getLogger(__name__)

def _get_active_provider(engine: PipelineEngine):
    config = engine.config_store.load()
    provider = engine.provider_registry.get(config.active_provider)
    return provider

async def analyze_relationships(job: Job, engine: PipelineEngine) -> None:
    """
    Analyze Relationships LLM Node.
    Takes abstractions produced by Identify Abstractions and forms a system diagram summary.
    """
    abstractions = job.abstractions.get("items", []) if job.abstractions else []
    if not abstractions:
        raise ValueError("No abstractions found in Job state. Cannot analyze relationships.")

    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    files_json = workspace_dir / "files.json"
    files_data: List[Tuple[str, str]] = json.loads(files_json.read_text(encoding="utf-8"))
    
    # Create context from abstraction names, indices, descriptions, and their related files
    context = "Identified Abstractions:\\n"
    all_relevant_indices = set()
    abstraction_info_for_prompt = []
    
    for i, abstr in enumerate(abstractions):
        file_indices_str = ", ".join(map(str, abstr["files"]))
        info_line = f"- Index {i}: {abstr['name']} (Relevant file indices: [{file_indices_str}])\\n  Description: {abstr['description']}"
        context += info_line + "\\n"
        abstraction_info_for_prompt.append(f"{i} # {abstr['name']}")
        all_relevant_indices.update(abstr.get("files", []))
        
    context += "\\nRelevant File Snippets (Referenced by Index and Path):\\n"
    file_context_str = ""
    for idx in sorted(list(all_relevant_indices)):
        if 0 <= idx < len(files_data):
            path, content = files_data[idx]
            file_context_str += f"--- File: {idx} # {path} ---\\n{content}\\n\\n"
    context += file_context_str

    
    abstraction_listing = "\n".join(abstraction_info_for_prompt)

    prompt = f"""
Based on the following abstractions and relevant code snippets from the project `{job.project_name}`:

List of Abstraction Indices and Names:
{abstraction_listing}

Context (Abstractions, Descriptions, Code):
{context}

Please provide:
1. A high-level `summary` of the project's main purpose and functionality in a few beginner-friendly sentences. Use markdown formatting with **bold** and *italic* text to highlight important concepts.
2. A list (`relationships`) describing the key interactions between these abstractions. For each relationship, specify:
    - `from_abstraction`: Index of the source abstraction (e.g., `0`)
    - `to_abstraction`: Index of the target abstraction (e.g., `1`)
    - `label`: A brief label for the interaction.

Format the output as YAML:

```yaml
summary: |
  A brief, simple explanation of the project.
relationships:
  - from_abstraction: 0
    to_abstraction: 1
    label: "Manages"
```

Now, provide the YAML output:
"""
    
    provider = _get_active_provider(engine)
    response = await asyncio.to_thread(provider.generate, GenerateRequest(prompt=prompt))
    
    yaml_str = extract_yaml_from_text(response.content)
    relationships_data = parse_yaml_safely(yaml_str)
    
    if not isinstance(relationships_data, dict):
        raise ValueError("LLM Output for Analyze Relationships is not a valid dict.")
        
    if "summary" not in relationships_data or "relationships" not in relationships_data:
        raise ValueError("Missing 'summary' or 'relationships' in Output.")
        
    if not isinstance(relationships_data["summary"], str):
        raise ValueError("'summary' must be string.")
        
    job.relationships = {
        "summary": relationships_data["summary"],
        "relationships": relationships_data["relationships"]
    }
