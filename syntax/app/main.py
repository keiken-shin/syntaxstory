from fastapi import FastAPI

from app.api.router import api_router
from app.config.store import ProviderConfigStore
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for SyntaxStory.",
    )

    app.state.settings = settings
    app.state.config_store = ProviderConfigStore(settings.provider_config_path)
    app.include_router(api_router)
    return app


app = create_app()
