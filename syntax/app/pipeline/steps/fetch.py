import asyncio
import json
from pathlib import Path
from app.pipeline.models import Job
from app.pipeline.engine import PipelineEngine
from app.crawler.service import CrawlerService
from app.crawler.models import CrawlerRequest

async def fetch_repo(job: Job, engine: PipelineEngine) -> None:
    """
    Crawl the repository, extract files safely, and persist to a job-specific workspace.
    """
    # In a full run, we would have real git cloning or GitHub API calls.
    # We write to `store.persistence_path.parent / "jobs" / job.id / files.json`
    
    service = CrawlerService()
    req = CrawlerRequest(url=job.repo_url, local_path=job.local_dir)
    result = await asyncio.to_thread(service.crawl_repository, req)
    
    if not result.success:
        first_error = result.errors[0].message if result.errors else "Unknown crawl error"
        raise RuntimeError(f"Crawl failed: {first_error}")
        
    workspace_dir = engine.store.persistence_path.parent / "jobs" / job.id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Exclude massive binaries, grab content & path
    files_data = [
        (item.path, item.content) 
        for item in result.manifest 
        if not item.binary and item.content
    ]
    
    files_json = workspace_dir / "files.json"
    files_json.write_text(json.dumps(files_data, indent=2), encoding="utf-8")
