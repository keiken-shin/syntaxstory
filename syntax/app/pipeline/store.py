import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from .models import Job

logger = logging.getLogger(__name__)

class JobStore:
    """
    JSON file-based persistent store for tracking generation jobs.
    This replaces ephemeral in-memory state scaling to handle concurrent background tasks safely.
    """
    
    def __init__(self, persistence_path: Path):
        self.persistence_path = persistence_path
        self._ensure_file()

    def _ensure_file(self):
        """Initializes empty JSON job tracker if none exists."""
        if not self.persistence_path.exists():
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            self.persistence_path.write_text("{}", encoding="utf-8")

    def _load_jobs(self) -> Dict[str, Job]:
        """Loads and parses all jobs."""
        try:
            content = self.persistence_path.read_text(encoding="utf-8")
            data = json.loads(content) if content.strip() else {}
            return {k: Job(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load jobs from {self.persistence_path}: {e}")
            return {}

    def _save_jobs(self, jobs: Dict[str, Job]):
        """Flushes the job map back to disk."""
        try:
            # We serialize to native python dicts then dump, to ensure clean Enum saving natively via pydantic
            data = {k: v.model_dump(mode='json') for k, v in jobs.items()}
            self.persistence_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to flush jobs to {self.persistence_path}: {e}")

    def save_job(self, job: Job) -> Job:
        """Upsert a Job entity."""
        jobs = self._load_jobs()
        jobs[job.id] = job
        self._save_jobs(jobs)
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a specific job by UUID."""
        jobs = self._load_jobs()
        return jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        """Get all pipeline jobs iteratively ordered by latest creation."""
        jobs = self._load_jobs()
        return sorted(list(jobs.values()), key=lambda j: j.created_at, reverse=True)
