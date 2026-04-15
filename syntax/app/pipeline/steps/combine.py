import logging
import os
from pathlib import Path

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)

async def combine_tutorial(job: Job, engine: PipelineEngine) -> None:
    """
    Combine Tutorial Node.
    Assembles the syllabus and chapter contents into a final Markdown artifact,
    and sets the `result_path` on the Job.
    """
    if not job.chapters:
        logger.warning(f"Job {job.id} has no chapters to combine.")
        job.result_path = None
        return

    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    tutorial_path = workspace_dir / "tutorial.md"
    
    lines = []
    lines.append(f"# {job.project_name} - Tutorial")
    
    if job.relationships and "summary" in job.relationships:
        lines.append("\n## Project Summary\n")
        lines.append(job.relationships["summary"])
        
    lines.append("\n## Syllabus\n")
    for chapter in job.chapters:
        lines.append(f"- {chapter.title}")
        
    lines.append("\n---\n")
    
    for idx, chapter in enumerate(job.chapters):
        if idx > 0:
            lines.append("\n---\n")
            
        lines.append(f"\n## {chapter.title}\n")
        if chapter.description:
            lines.append(f"**Brief**: {chapter.description}\n")
            
        lines.append(f"\n{chapter.content}\n")
        
    tutorial_content = "\n".join(lines)
    
    with open(tutorial_path, "w", encoding="utf-8") as f:
        f.write(tutorial_content)
        
    job.result_path = str(tutorial_path)
    logger.info(f"Job {job.id} combined tutorial into {job.result_path}")
