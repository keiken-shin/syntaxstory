import logging
import os
from pathlib import Path
import re

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)

async def combine_tutorial(job: Job, engine: PipelineEngine) -> None:
    if not job.chapters:
        logger.warning(f"Job {job.id} has no chapters to combine.")
        job.result_path = None
        return

    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    mermaid_lines = ["```mermaid", "graph TD"]
    abstractions = job.abstractions.get("items", []) if job.abstractions else []
    for idx, abs_item in enumerate(abstractions):
        safe_name = f"A{idx}"
        display_name = abs_item.get("name", f"Concept {idx}").replace('"', '')
        mermaid_lines.append(f'    {safe_name}["{display_name}"]')
        
    rels = job.relationships.get("relationships", []) if job.relationships else []
    for rel in rels:
        f_idx = rel.get("from_abstraction")
        t_idx = rel.get("to_abstraction")
        lbl = rel.get("label", "").replace('"', '')
        if f_idx is not None and t_idx is not None:
            mermaid_lines.append(f'    A{f_idx} -->|"{lbl}"| A{t_idx}')
            
    mermaid_lines.append("```")
    mermaid = "\n".join(mermaid_lines)
    
    chapter_links = []
    total_chapters = len(job.chapters)
    
    def get_filename(idx, chapter_obj):
        chapter_num = idx + 1
        safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', chapter_obj.title).strip('-').lower()
        return f"chapter-{chapter_num}-{safe_title}.md"
        
    for idx, chapter in enumerate(job.chapters):
        chapter_num = idx + 1
        file_name = get_filename(idx, chapter)
        chapter_path = workspace_dir / file_name
        
        content_lines = [f"# {chapter.title}", ""]
        if chapter.description:
            content_lines.append(f"**Brief**: {chapter.description}\n")
            
        content_lines.append(chapter.content)
        content_lines.append("\n---")
        
        nav_lines = []
        if idx > 0:
            nav_lines.append(f"[< Previous]({get_filename(idx - 1, job.chapters[idx - 1])})")
        nav_lines.append("[Index](index.md)")
        if idx < total_chapters - 1:
            nav_lines.append(f"[Next >]({get_filename(idx + 1, job.chapters[idx + 1])})")
            
        content_lines.append(" | ".join(nav_lines))
        
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
            
        chapter_links.append(f"- [Chapter {chapter_num}: {chapter.title}]({file_name})")
        
    index_path = workspace_dir / "index.md"
    index_lines = [f"# {job.project_name} - Tutorial", ""]
    if job.relationships and "summary" in job.relationships:
        index_lines.append("## Project Summary\n" + job.relationships["summary"] + "\n")
        
    index_lines.append("## Architecture\n" + mermaid + "\n")
    index_lines.append("## Syllabus")
    index_lines.extend(chapter_links)
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))
        
    job.result_path = str(index_path)
