import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.pipeline.models import Job, PipelineStep, JobStatus
from app.pipeline.engine import PipelineEngine
from app.pipeline.store import JobStore

# Import the steps
from app.pipeline.steps.fetch import fetch_repo
from app.pipeline.steps.identify import identify_abstractions
from app.pipeline.steps.analyze import analyze_relationships

@pytest.fixture
def mock_engine(tmp_path):
    store = JobStore(tmp_path / "jobs.json")
    engine = PipelineEngine(store=store)
    return engine

@pytest.fixture
def dummy_job(mock_engine):
    job = Job(id="test-job-id", project_name="TestProject", repo_url="mock_url")
    mock_engine.store.save_job(job)
    return job

@pytest.fixture
def setup_dummy_files(dummy_job, mock_engine):
    # Setup dummy workspace files.json
    workspace_dir = mock_engine.store.persistence_path.parent / "jobs" / dummy_job.id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    files_data = [
        ("src/main.py", "def main():\\n    print('hello world')"),
        ("src/utils.py", "def helper():\\n    pass")
    ]
    (workspace_dir / "files.json").write_text(json.dumps(files_data), encoding="utf-8")

@pytest.mark.anyio
async def test_identify_abstractions_success(dummy_job, mock_engine, setup_dummy_files):
    # The StubProvider returns fake YAML outputs for prompts containing "```yaml" (added in this PR)
    # We just run identify_abstractions ensuring it parses and patches State
    await identify_abstractions(dummy_job, mock_engine)
    
    assert dummy_job.abstractions is not None
    assert "items" in dummy_job.abstractions
    
    abstractions = dummy_job.abstractions["items"]
    assert len(abstractions) == 1
    assert abstractions[0]["name"] == "Stub Abstraction"
    assert abstractions[0]["files"] == [0]

@pytest.mark.anyio
async def test_analyze_relationships_success(dummy_job, mock_engine, setup_dummy_files):
    # Pre-seed identified abstractions for AnalyzeRelationships
    dummy_job.abstractions = {
        "items": [
            {
                "name": "Stub Abstraction",
                "description": "Desc here.",
                "files": [0, 1]
            }
        ]
    }
    
    await analyze_relationships(dummy_job, mock_engine)
    
    assert dummy_job.relationships is not None
    assert "summary" in dummy_job.relationships
    assert "relationships" in dummy_job.relationships
    
    rel = dummy_job.relationships["relationships"]
    assert len(rel) == 1
    assert rel[0]["from_abstraction"] == 0
    assert rel[0]["label"] == "Uses"

@pytest.mark.anyio
async def test_identify_abstractions_missing_files_fails(dummy_job, mock_engine):
    # Run WITHOUT setup_dummy_files which means files.json won't exist
    with pytest.raises(FileNotFoundError):
        await identify_abstractions(dummy_job, mock_engine)

@pytest.mark.anyio
async def test_analyze_relationships_missing_abstractions_fails(dummy_job, mock_engine, setup_dummy_files):
    # Analyze requires identify to run first
    with pytest.raises(ValueError, match="No abstractions found"):
        await analyze_relationships(dummy_job, mock_engine)

from app.pipeline.steps.order import order_chapters

@pytest.mark.anyio
async def test_order_chapters_success(dummy_job, mock_engine):
    dummy_job.abstractions = {
        "items": [
            {
                "name": "Stub Abstraction",
                "description": "Desc here.",
                "files": [0, 1]
            }
        ]
    }
    dummy_job.relationships = {
        "summary": "Test stub summary.",
        "relationships": [
            {
                "from_abstraction": 0,
                "to_abstraction": 0,
                "label": "Uses"
            }
        ]
    }

    await order_chapters(dummy_job, mock_engine)

    assert dummy_job.syllabus is not None
    assert len(dummy_job.syllabus) == 1
    assert dummy_job.syllabus[0]["chapter_number"] == 1
    assert dummy_job.syllabus[0]["abstraction_index"] == 0
    assert dummy_job.syllabus[0]["name"] == "Stub Abstraction"

@pytest.mark.anyio
async def test_order_chapters_missing_data_fails(dummy_job, mock_engine):
    with pytest.raises(ValueError, match="missing abstractions"):
        await order_chapters(dummy_job, mock_engine)

