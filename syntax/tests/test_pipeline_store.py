import pytest
import json
from pathlib import Path
from datetime import datetime, UTC
from app.pipeline.models import Job, JobStatus, PipelineStep, Chapter
from app.pipeline.store import JobStore

@pytest.fixture
def temp_job_store(tmp_path):
    store_file = tmp_path / "jobs_test.json"
    return JobStore(persistence_path=store_file)

def test_job_store_initializes_empty_file(tmp_path):
    store_file = tmp_path / "init_test.json"
    store = JobStore(persistence_path=store_file)
    assert store_file.exists()
    assert store_file.read_text() == "{}"
    
def test_job_store_save_and_get(temp_job_store):
    job = Job(project_name="my_project", repo_url="https://github.com/abc/xyz")
    saved_job = temp_job_store.save_job(job)
    
    fetched_job = temp_job_store.get_job(saved_job.id)
    assert fetched_job is not None
    assert fetched_job.id == saved_job.id
    assert fetched_job.project_name == "my_project"
    assert fetched_job.status == JobStatus.PENDING
    assert fetched_job.current_step == PipelineStep.FETCH_REPO

def test_job_store_list_jobs(temp_job_store):
    job1 = Job(project_name="project1")
    job2 = Job(project_name="project2")
    temp_job_store.save_job(job1)
    temp_job_store.save_job(job2)
    
    jobs = temp_job_store.list_jobs()
    assert len(jobs) == 2
    
    names = [j.project_name for j in jobs]
    assert "project1" in names
    assert "project2" in names

def test_job_store_update_job(temp_job_store):
    job = Job(project_name="update_target")
    saved_job = temp_job_store.save_job(job)
    
    # Update job state manually
    saved_job.status = JobStatus.RUNNING
    saved_job.current_step = PipelineStep.IDENTIFY_ABSTRACTIONS
    saved_job.progress = 20
    saved_job.error = "something transient"
    
    # Push down
    temp_job_store.save_job(saved_job)
    
    # Reload and assert changes persist
    fetched_job = temp_job_store.get_job(saved_job.id)
    assert fetched_job.status == JobStatus.RUNNING
    assert fetched_job.current_step == PipelineStep.IDENTIFY_ABSTRACTIONS
    assert fetched_job.progress == 20
    assert fetched_job.error == "something transient"

def test_job_store_complex_datatypes(temp_job_store):
    # Test dictionaries, enums and chapter sub-models write safely to json
    chapters = [Chapter(title="The Beginning"), Chapter(title="The End")]
    job = Job(
        project_name="complex_job",
        abstractions={"key": "val"},
        chapters=chapters
    )
    saved = temp_job_store.save_job(job)
    fetched = temp_job_store.get_job(saved.id)
    
    assert fetched.abstractions == {"key": "val"}
    assert len(fetched.chapters) == 2
    assert fetched.chapters[0].title == "The Beginning"
    assert fetched.chapters[1].status == JobStatus.PENDING