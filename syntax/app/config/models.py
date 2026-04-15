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


class ProviderSecretsPublic(BaseModel):
    """Secrets contract exposed by the API — key value is always redacted."""

    has_api_key: bool


class ProviderConfigPublic(BaseModel):
    """Redacted per-provider config safe to include in API responses."""

    provider_id: ProviderId
    enabled: bool
    model: str
    base_url: str | None
    secrets: ProviderSecretsPublic

    @classmethod
    def from_config(cls, cfg: ProviderConfig) -> "ProviderConfigPublic":
        return cls(
            provider_id=cfg.provider_id,
            enabled=cfg.enabled,
            model=cfg.model,
            base_url=cfg.base_url,
            secrets=ProviderSecretsPublic(has_api_key=bool(cfg.secrets.api_key)),
        )


class RuntimeProviderConfigPublic(BaseModel):
    """Full runtime config response — no secrets exposed."""

    active_provider: ProviderId
    fallback_provider: ProviderId | None
    providers: list[ProviderConfigPublic]

    @classmethod
    def from_config(cls, cfg: RuntimeProviderConfig) -> "RuntimeProviderConfigPublic":
        return cls(
            active_provider=cfg.active_provider,
            fallback_provider=cfg.fallback_provider,
            providers=[
                ProviderConfigPublic.from_config(p) for p in cfg.providers.values()
            ],
        )


class UpdateProviderRequest(BaseModel):
    """Payload to update a single provider's config."""

    provider_id: ProviderId
    enabled: bool | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class SetActiveProviderRequest(BaseModel):
    """Payload to switch the active (and optionally fallback) provider."""

    active_provider: ProviderId
    fallback_provider: ProviderId | None = None


class ProviderTestResponse(BaseModel):
    """Response from POST /config/providers/{provider_id}/test."""

    provider_id: ProviderId
    success: bool
    latency_ms: float | None = None
    error: str | None = None
