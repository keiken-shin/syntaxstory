import logging
from typing import Dict, Awaitable, Callable
from .models import Job, JobStatus, PipelineStep
from .store import JobStore

logger = logging.getLogger(__name__)

# Canonical sequence of pipeline steps in order
STEP_SEQUENCE = [
    PipelineStep.FETCH_REPO,
    PipelineStep.IDENTIFY_ABSTRACTIONS,
    PipelineStep.ANALYZE_RELATIONSHIPS,
    PipelineStep.ORDER_CHAPTERS,
    PipelineStep.WRITE_CHAPTERS,
    PipelineStep.COMBINE_TUTORIAL
]

class PipelineEngine:
    """
    State machine execution engine for the tutorial generation jobs.
    Runs asynchronous node handlers, tracks state transitions, and persists results.
    """
    
    def __init__(self, store: JobStore):
        self.store = store
        self.handlers: Dict[PipelineStep, Callable[[Job], Awaitable[None]]] = {}

    def register_step(self, step: PipelineStep, handler: Callable[[Job], Awaitable[None]]) -> None:
        """Register an async handler function for a specific pipeline step."""
        self.handlers[step] = handler

    async def run_job(self, job_id: str) -> None:
        """
        Retrieves a job by ID, executes its remaining steps in sequence, 
        and updates the central JSON store continuously.
        """
        job = self.store.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found in store.")
            return

        if job.status == JobStatus.COMPLETED:
            logger.info(f"Job {job_id} is already completed.")
            return

        # Transition to RUNNING state
        job.status = JobStatus.RUNNING
        job.error = None
        self.store.save_job(job)

        try:
            while job.status == JobStatus.RUNNING:
                current_step = job.current_step
                handler = self.handlers.get(current_step)

                if not handler:
                    raise NotImplementedError(f"No handler registered for step: {current_step}")

                logger.info(f"Job {job.id} starting step: {current_step}")
                
                # Execute the discrete step logic
                await handler(job)
                
                # Progress state
                try:
                    current_index = STEP_SEQUENCE.index(current_step)
                    if current_index + 1 < len(STEP_SEQUENCE):
                        # Advance to the next step
                        next_step = STEP_SEQUENCE[current_index + 1]
                        job.current_step = next_step
                        job.progress = int(((current_index + 1) / len(STEP_SEQUENCE)) * 100)
                        self.store.save_job(job)
                    else:
                        # Reached the end of the sequence
                        job.status = JobStatus.COMPLETED
                        job.progress = 100
                        self.store.save_job(job)
                        break
                except ValueError:
                    raise ValueError(f"Unknown step {current_step} encountered.")

        except Exception as e:
            logger.exception(f"Job {job.id} failed at step {job.current_step}: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            self.store.save_job(job)
