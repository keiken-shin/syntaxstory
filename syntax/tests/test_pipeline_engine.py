import pytest
import asyncio
from app.pipeline.models import Job, JobStatus, PipelineStep
from app.pipeline.store import JobStore
from app.pipeline.engine import PipelineEngine

@pytest.fixture
def memory_store(tmp_path):
    return JobStore(tmp_path / "test_engine_jobs.json")

@pytest.fixture
def engine(memory_store):
    return PipelineEngine(store=memory_store)

@pytest.mark.anyio
async def test_pipeline_engine_runs_to_completion(memory_store, engine):
    job = Job(project_name="success_test")
    memory_store.save_job(job)
    
    # Store visited steps to assert execution order
    visited = []
    
    async def generic_handler(step_name):
        async def handler(j: Job):
            visited.append(step_name)
        return handler
        
    engine.register_step(PipelineStep.FETCH_REPO, await generic_handler("FETCH_REPO"))
    engine.register_step(PipelineStep.IDENTIFY_ABSTRACTIONS, await generic_handler("IDENTIFY_ABSTRACTIONS"))
    engine.register_step(PipelineStep.ANALYZE_RELATIONSHIPS, await generic_handler("ANALYZE_RELATIONSHIPS"))
    engine.register_step(PipelineStep.ORDER_CHAPTERS, await generic_handler("ORDER_CHAPTERS"))
    engine.register_step(PipelineStep.WRITE_CHAPTERS, await generic_handler("WRITE_CHAPTERS"))
    engine.register_step(PipelineStep.COMBINE_TUTORIAL, await generic_handler("COMBINE_TUTORIAL"))
    
    await engine.run_job(job.id)
    
    # Re-fetch from store to test transitions
    updated_job = memory_store.get_job(job.id)
    
    assert updated_job.status == JobStatus.COMPLETED
    assert updated_job.progress == 100
    assert updated_job.error is None
    
    # Assert every step ran sequentially
    assert visited == [
        "FETCH_REPO",
        "IDENTIFY_ABSTRACTIONS",
        "ANALYZE_RELATIONSHIPS",
        "ORDER_CHAPTERS",
        "WRITE_CHAPTERS",
        "COMBINE_TUTORIAL"
    ]

@pytest.mark.anyio
async def test_pipeline_engine_transitions_to_failed(memory_store, engine):
    job = Job(project_name="failure_test")
    memory_store.save_job(job)
    
    visited = []
    
    async def passing_handler(j: Job):
        visited.append(j.current_step)
        
    async def failing_handler(j: Job):
        visited.append(j.current_step)
        raise ValueError("Simulated pipeline failure")

    engine.register_step(PipelineStep.FETCH_REPO, passing_handler)
    # The pipeline should crash on IDENTIFY_ABSTRACTIONS
    engine.register_step(PipelineStep.IDENTIFY_ABSTRACTIONS, failing_handler)
    engine.register_step(PipelineStep.ANALYZE_RELATIONSHIPS, passing_handler) # Never reached
    
    await engine.run_job(job.id)
    
    updated_job = memory_store.get_job(job.id)
    
    assert updated_job.status == JobStatus.FAILED
    assert updated_job.error == "Simulated pipeline failure"
    assert updated_job.current_step == PipelineStep.IDENTIFY_ABSTRACTIONS
    assert len(visited) == 2

@pytest.mark.anyio
async def test_pipeline_engine_missing_handler_raises_not_implemented(memory_store, engine):
    job = Job(project_name="missing_handler_test")
    memory_store.save_job(job)
    
    # We don't register any handlers
    await engine.run_job(job.id)
    
    updated_job = memory_store.get_job(job.id)
    
    assert updated_job.status == JobStatus.FAILED
    assert "No handler registered for step" in updated_job.error
