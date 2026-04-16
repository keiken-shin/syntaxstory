from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.pipeline.models import Job, JobStatus
from app.pipeline.engine import PipelineEngine
from app.pipeline.store import JobStore

router = APIRouter(prefix="/jobs", tags=["pipeline"])

class CreateJobRequest(BaseModel):
    project_name: str
    repo_url: str

class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus

def get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store

def get_pipeline_engine(request: Request) -> PipelineEngine:
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
