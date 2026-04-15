from pydantic import BaseModel, Field

from app.llm.providers.base import ProviderId


class ProviderSecrets(BaseModel):
    api_key: str | None = None


class ProviderConfig(BaseModel):
    provider_id: ProviderId
    enabled: bool = True
    model: str = ""
    base_url: str | None = None
    secrets: ProviderSecrets = Field(default_factory=ProviderSecrets)


class RuntimeProviderConfig(BaseModel):
    active_provider: ProviderId = ProviderId.GEMINI
    fallback_provider: ProviderId | None = None
    providers: dict[ProviderId, ProviderConfig]

    @classmethod
    def default(cls) -> "RuntimeProviderConfig":
        return cls(
            active_provider=ProviderId.GEMINI,
            fallback_provider=ProviderId.OPENAI,
            providers={
                ProviderId.GEMINI: ProviderConfig(
                    provider_id=ProviderId.GEMINI,
                    model="gemini-2.5-pro",
                ),
                ProviderId.OPENAI: ProviderConfig(
                    provider_id=ProviderId.OPENAI,
                    model="gpt-4o-mini",
                    base_url="https://api.openai.com/v1",
                ),
                ProviderId.ANTHROPIC: ProviderConfig(
                    provider_id=ProviderId.ANTHROPIC,
                    model="claude-3-7-sonnet-latest",
                    base_url="https://api.anthropic.com",
                ),
                ProviderId.OLLAMA: ProviderConfig(
                    provider_id=ProviderId.OLLAMA,
                    model="llama3.2",
                    base_url="http://localhost:11434",
                ),
            },
        )
