from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import os
import uuid
import asyncio

# Using the references code as the core pipeline
from .flow import create_tutorial_flow

app = FastAPI(
    title="SyntaxStory Backend",
    description="Tutorial Generation API powered by GitHub APIs & LLMs",
    version="0.1.0",
)

# In-memory "job list" for demonstration of doing it step-by-step
jobs_db = {}

class TutorialRequest(BaseModel):
    repo_url: str
    github_token: str | None = None
    language: str = "english"
    no_cache: bool = False
    max_abstractions: int = 10
    
class JobResponse(BaseModel):
    job_id: str
    status: str

def run_tutorial_flow(job_id: str, request_data: dict):
    """
    Background task wrapper that runs the reference architecture flow.
    """
    try:
        jobs_db[job_id]["status"] = "in_progress"
        
        # Setup shared state for the flow just like the CLI did
        shared = {
            "repo_url": request_data.get("repo_url"),
            "local_dir": None,
            "project_name": None,
            "github_token": request_data.get("github_token") or os.environ.get('GITHUB_TOKEN'),
            "output_dir": f"output/{job_id}",
            
            # Defaults
            "include_patterns": {
                "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.pyi", "*.pyx",
                "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "*Dockerfile",
                "*Makefile", "*.yaml", "*.yml"
            },
            "exclude_patterns": {
                "assets/*", "data/*", "images/*", "public/*", "static/*", "temp/*",
                "*docs/*", "*venv/*", "*.venv/*", "*test*", "*tests/*", "*examples/*",
                "v1/*", "*dist/*", "*build/*", "*experimental/*", "*deprecated/*", "*misc/*",
                "*legacy/*", ".git/*", ".github/*", ".next/*", ".vscode/*", "*obj/*", "*bin/*",
                "*node_modules/*", "*.log"
            },
            "max_file_size": 100000,
            "language": request_data.get("language", "english"),
            "use_cache": not request_data.get("no_cache", False),
            "max_abstraction_num": request_data.get("max_abstractions", 10),
            
            # Outputs populated by nodes
            "files": [],
            "abstractions": [],
            "relationships": {},
            "chapter_order": [],
            "chapters": [],
            "final_output_dir": None
        }

        # Instead of abstracting, use the references flow directly
        tutorial_flow = create_tutorial_flow()
        tutorial_flow.run(shared)
        
        jobs_db[job_id]["status"] = "success"
        jobs_db[job_id]["result_path"] = shared.get("final_output_dir")
        
    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)


@app.post("/api/v1/tutorials", response_model=JobResponse)
async def create_tutorial(req: TutorialRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "pending"
    }

    # Run the imported core reference process in the background
    background_tasks.add_task(run_tutorial_flow, job_id, req.dict())
    
    return JobResponse(job_id=job_id, status="pending")

@app.get("/api/v1/tutorials/{job_id}")
async def get_tutorial_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs_db[job_id]
