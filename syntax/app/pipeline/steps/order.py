import asyncio
import logging
from typing import List, Any
import yaml

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine
from app.llm.parser import extract_yaml_from_text, parse_yaml_safely
from app.llm.providers.base import GenerateRequest
from app.llm.cache import cached_generate

logger = logging.getLogger(__name__)

def _get_active_provider(engine: PipelineEngine):
    config = engine.config_store.load()
    provider = engine.provider_registry.get(config.active_provider, config.providers[config.active_provider])
    return provider

async def order_chapters(job: Job, engine: PipelineEngine) -> None:
    """
    Order Chapters LLM Node.
    Determines the best logical sequence to explain the identified abstractions
    and creates a structured syllabus.
    """
    if not job.abstractions or "items" not in job.abstractions:
        raise ValueError(f"Job {job.id} missing abstractions.")
    if not job.relationships or "summary" not in job.relationships or "relationships" not in job.relationships:
        raise ValueError(f"Job {job.id} missing relationships.")

    abstractions = job.abstractions["items"]
    relationships = job.relationships

    num_abstractions = len(abstractions)
    if num_abstractions == 0:
        logger.warning(f"Job {job.id} has 0 abstractions. Creating empty syllabus.")
        job.syllabus = []
        return

    # Prepare context for the prompt
    abstraction_info_for_prompt = []
    for i, abstraction in enumerate(abstractions):
        abstraction_info_for_prompt.append(f"- {i} # {abstraction['name']}")
    abstraction_listing = "\n".join(abstraction_info_for_prompt)

    context = f"Project Summary:\n{relationships['summary']}\n\n"
    context += "Relationships (Indices refer to abstractions above):\n"
    for rel in relationships["relationships"]:
        from_idx = rel.get("from_abstraction")
        to_idx = rel.get("to_abstraction")
        
        # Ensure indices exist properly, skip if missing or malformed
        if from_idx is None or to_idx is None:
            continue
        if not (0 <= from_idx < num_abstractions) or not (0 <= to_idx < num_abstractions):
            continue

        from_name = abstractions[from_idx]["name"]
        to_name = abstractions[to_idx]["name"]
        label = rel.get("label", "Unknown relationship")
        context += f"- From {from_idx} ({from_name}) to {to_idx} ({to_name}): {label}\n"

    # LLM Prompt for Sequence
    prompt = f"""
Given the following project abstractions and their relationships for the project `{job.project_name}`:

Abstractions (Index # Name):
{abstraction_listing}

Context about relationships and project summary:
{context}

If you are going to make a tutorial for `{job.project_name}`, what is the best order to explain these abstractions, from first to last?
Ideally, first explain those that are the most important or foundational, perhaps user-facing concepts or entry points. Then move to more detailed, lower-level implementation details or supporting concepts.

Output the ordered list of abstraction indices, including the name in a comment for clarity. Use the format `- idx # AbstractionName`.

```yaml
- 2 # FoundationalConcept
- 0 # CoreClassA
- 1 # CoreClassB (uses CoreClassA)
```

Now, provide the YAML output:
"""

    provider = _get_active_provider(engine)
    response = await asyncio.to_thread(cached_generate, provider, GenerateRequest(prompt=prompt))

    # Extraction & Parsing Validation
    yaml_str = extract_yaml_from_text(response.content)
    ordered_indices_raw = parse_yaml_safely(yaml_str)

    if not isinstance(ordered_indices_raw, list):
        raise ValueError("LLM Output for Order Chapters is not a valid list.")

    ordered_indices = []
    seen_indices = set()

    for entry in ordered_indices_raw:
        idx = -1
        try:
            if isinstance(entry, int):
                idx = entry
            elif isinstance(entry, str) and "#" in entry:
                idx = int(entry.split("#")[0].strip())
            else:
                idx = int(str(entry).strip())
        except (ValueError, TypeError):
            continue # Gracefully skip unparsable entries

        if not (0 <= idx < num_abstractions):
            continue # Out of bounds
        
        if idx in seen_indices:
            continue # Skip duplicates
        
        seen_indices.add(idx)
        ordered_indices.append(idx)

    # Cross-referential validation
    missing_indices = set(range(num_abstractions)) - seen_indices
    if missing_indices:
        logger.warning(f"LLM omitted abstraction indices: {missing_indices}. Appending to the end of the syllabus.")
        ordered_indices.extend(list(missing_indices))

    # Form the syllabus explicitly
    syllabus = []
    for order_num, abs_idx in enumerate(ordered_indices, start=1):
        syllabus.append({
            "chapter_number": order_num,
            "abstraction_index": abs_idx,
            "name": abstractions[abs_idx]["name"]
        })

    job.syllabus = syllabus
    logger.info(f"Job {job.id} generated a syllabus mapped to {len(syllabus)} chapters.")
