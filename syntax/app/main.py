from pathlib import Path
from fastapi import FastAPI

from app.api.router import api_router
from app.config.store import ProviderConfigStore
from app.core.settings import get_settings
from app.llm.provider_registry import build_default_provider_registry
from app.pipeline.store import JobStore
from app.pipeline.engine import PipelineEngine

from app.pipeline.models import PipelineStep
from app.pipeline.steps.fetch import fetch_repo
from app.pipeline.steps.identify import identify_abstractions
from app.pipeline.steps.analyze import analyze_relationships
from app.pipeline.steps.order import order_chapters
from app.pipeline.steps.write import write_chapters
from app.pipeline.steps.combine import combine_tutorial


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for SyntaxStory.",
    )

    app.state.settings = settings
    app.state.config_store = ProviderConfigStore(settings.provider_config_path)
    app.state.provider_registry = build_default_provider_registry()
    
    # Initialize Pipeline Components
    app.state.job_store = JobStore(Path("storage/jobs.json"))
    
    engine = PipelineEngine(store=app.state.job_store)
    # Give the engine references to global config/registry to avoid hardcoded paths in steps
    engine.provider_registry = app.state.provider_registry
    engine.config_store = app.state.config_store

    engine.register_step(PipelineStep.FETCH_REPO, fetch_repo)
    engine.register_step(PipelineStep.IDENTIFY_ABSTRACTIONS, identify_abstractions)
    engine.register_step(PipelineStep.ANALYZE_RELATIONSHIPS, analyze_relationships)
    engine.register_step(PipelineStep.ORDER_CHAPTERS, order_chapters)
    engine.register_step(PipelineStep.WRITE_CHAPTERS, write_chapters)
    engine.register_step(PipelineStep.COMBINE_TUTORIAL, combine_tutorial)
    
    app.state.pipeline_engine = engine

    app.include_router(api_router)
    return app


app = create_app()
