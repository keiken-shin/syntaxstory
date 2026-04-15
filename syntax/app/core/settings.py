from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "SyntaxStory API"
    app_version: str = "0.1.0"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SYNTAX_STORY_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
