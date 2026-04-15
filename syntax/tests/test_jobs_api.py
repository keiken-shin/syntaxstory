import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.models import JobStatus

client = TestClient(app)

def test_create_job():
    payload = {
        "project_name": "Test Project",
        "repo_url": "https://github.com/mock/mock"
    }
    # It must return 202 Accepted
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == JobStatus.PENDING
    
    # Validate the GET endpoint returns it too
    job_id = data["job_id"]
    get_resp = client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    
    get_data = get_resp.json()
    assert get_data["id"] == job_id
    assert get_data["project_name"] == "Test Project"
    # With TestClient, background tasks execute synchronously after the POST returns,
    # so the GET will instantly see the final state (FAILED because mock/mock isn't real)
    assert get_data["status"] in [JobStatus.PENDING, JobStatus.FAILED, JobStatus.COMPLETED]

def test_get_missing_job():
    response = client.get("/api/jobs/not-a-real-job-id")
    assert response.status_code == 404
