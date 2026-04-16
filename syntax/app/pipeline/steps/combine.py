import logging
import os
from pathlib import Path
import re

from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)

async def combine_tutorial(job: Job, engine: PipelineEngine) -> None:
    """
    Combine Tutorial Node.
    Assembles the syllabus and chapter contents into a multi-file Markdown artifact
    including a Mermaid.js diagram and an index.md file. sets the `result_path` on the Job.
    """
    if not job.chapters:
        logger.warning(f"Job {job.id} has no chapters to combine.")
        job.result_path = None
        return

    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate the Mermaid diagram
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
    
    # 2. Write individual chapter files and collect links
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
        
        content_lines = [
            f"# {chapter.title}",
            ""
        ]
        
        if chapter.description:
            content_lines.append(f"**Brief**: {chapter.description}")
            content_lines.append("")
            
        content_lines.append(chapter.content)
        content_lines.append("")
        content_lines.append("---")
        
        nav_lines = []
        if idx > 0:
            prev_file = get_filename(idx - 1, job.chapters[idx - 1])
            nav_lines.append(f"[< Previous]({prev_file})")
            
        nav_lines.append("[Index](index.md)")
            
        if idx < total_chapters - 1:
            next_file = get_filename(idx + 1, job.chapters[idx + 1])
            nav_lines.append(f"[Next >]({next_file})")
            
        content_lines.append(" | ".join(nav_lines))
        
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
            
        chapter_links.append(f"- [Chapter {chapter_num}: {chapter.title}]({file_name})")
        
    # 3. Write index.md
    index_path = workspace_dir / "index.md"
    
    index_lines = [
        f"# {job.project_name} - Tutorial",
        ""
    ]
    
    if job.relationships and "summary" in job.relationships:
        index_lines.append("## Project Summary")
        index_lines.append(job.relationships["summary"])
        index_lines.append("")
        
    index_lines.append("## Architecture")
    index_lines.append(mermaid)
    index_lines.append("")
    
    index_lines.append("## Syllabus")
    index_lines.extend(chapter_links)
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))
        
    job.result_path = str(index_path)
    logger.info(f"Job {job.id} combined into {job.result_path} multi-file output.")
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
