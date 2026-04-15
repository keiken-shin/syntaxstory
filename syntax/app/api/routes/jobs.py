from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.pipeline.models import Job, JobStatus
from app.pipeline.engine import PipelineEngine
from app.pipeline.store import JobStore

# Need the steps to register them to engine
from app.pipeline.models import PipelineStep
from app.pipeline.steps.fetch import fetch_repo
from app.pipeline.steps.identify import identify_abstractions
from app.pipeline.steps.analyze import analyze_relationships
from app.pipeline.steps.order import order_chapters
from app.pipeline.steps.write import write_chapters
from app.pipeline.steps.combine import combine_tutorial

router = APIRouter(prefix="/jobs", tags=["pipeline"])

class CreateJobRequest(BaseModel):
    project_name: str
    repo_url: str

class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus

def get_job_store(request: Request) -> JobStore:
    # app.state might not have it yet, we need to create it or read it
    # We should inject it into app.state at startup, but for now we'll do what is available
    if not hasattr(request.app.state, "job_store"):
        # Default store path
        from pathlib import Path
        store_path = Path("storage/jobs.json")
        request.app.state.job_store = JobStore(store_path)
    return request.app.state.job_store

def get_pipeline_engine(request: Request, job_store: JobStore = Depends(get_job_store)) -> PipelineEngine:
    if not hasattr(request.app.state, "pipeline_engine"):
        engine = PipelineEngine(store=job_store)
        
        # Register handlers
        engine.register_step(PipelineStep.FETCH_REPO, fetch_repo)
        engine.register_step(PipelineStep.IDENTIFY_ABSTRACTIONS, identify_abstractions)
        engine.register_step(PipelineStep.ANALYZE_RELATIONSHIPS, analyze_relationships)
        engine.register_step(PipelineStep.ORDER_CHAPTERS, order_chapters)
        engine.register_step(PipelineStep.WRITE_CHAPTERS, write_chapters)
        engine.register_step(PipelineStep.COMBINE_TUTORIAL, combine_tutorial)
        
        request.app.state.pipeline_engine = engine
    return request.app.state.pipeline_engine

async def run_pipeline_background(job_id: str, engine: PipelineEngine):
    await engine.run_job(job_id)

@router.post("", response_model=CreateJobResponse, status_code=202)
def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    store: JobStore = Depends(get_job_store),
    engine: PipelineEngine = Depends(get_pipeline_engine)
):
    """Trigger a new tutorial generation pipeline."""
    job = Job(project_name=payload.project_name, repo_url=payload.repo_url)
    store.save_job(job)
    
    # Trigger background execution
    background_tasks.add_task(run_pipeline_background, job.id, engine)
    
    return CreateJobResponse(job_id=job.id, status=job.status)

@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str, store: JobStore = Depends(get_job_store)):
    """Get the state of an ongoing or completed job."""
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
