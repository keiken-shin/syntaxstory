from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, UTC
import uuid

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"

class PipelineStep(str, Enum):
    FETCH_REPO = "fetch_repo"
    IDENTIFY_ABSTRACTIONS = "identify_abstractions"
    ANALYZE_RELATIONSHIPS = "analyze_relationships"
    ORDER_CHAPTERS = "order_chapters"
    WRITE_CHAPTERS = "write_chapters"
    COMBINE_TUTORIAL = "combine_tutorial"

class Chapter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    error: Optional[str] = None

class Job(BaseModel):
    """
    Represents the full state of a tutorial generation pipeline.
    This model serves as the single source of truth for the job and is stored persistently.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Metadata
    project_name: str
    repo_url: Optional[str] = None
    local_dir: Optional[str] = None
    
    # Flow state
    status: JobStatus = JobStatus.PENDING
    current_step: PipelineStep = PipelineStep.FETCH_REPO
    progress: int = 0
    error: Optional[str] = None
    
    # Generation artefacts (produced by nodes)
    abstractions: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None
    syllabus: Optional[List[Dict[str, Any]]] = None # Expected outlines from LLM
    chapters: Optional[List[Chapter]] = None
    
    # Final output
    result_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
