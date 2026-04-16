from fastapi import APIRouter, HTTPException

from app.config.deps import ConfigStoreDep
from app.config.models import (
    ProviderConfigPublic,
    ProviderTestResponse,
    RuntimeProviderConfigPublic,
    SetActiveProviderRequest,
    UpdateProviderRequest,
)
from app.llm.deps import ProviderRegistryDep
from app.llm.providers.base import ProviderId

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
def list_providers(store: ConfigStoreDep) -> RuntimeProviderConfigPublic:
    """Return the full runtime provider configuration with secrets redacted."""
    config = store.load()
    return RuntimeProviderConfigPublic.from_config(config)


@router.get("/providers/{provider_id}")
def get_provider(
    provider_id: ProviderId,
    store: ConfigStoreDep,
) -> ProviderConfigPublic:
    """Return a single provider's config with secrets redacted."""
    config = store.load()
    if provider_id not in config.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return ProviderConfigPublic.from_config(config.providers[provider_id])


@router.patch("/provider")
def update_provider(
    body: UpdateProviderRequest,
    store: ConfigStoreDep,
) -> ProviderConfigPublic:
    """
    Partially update a provider's config.

    All fields are optional; only non-None values are applied.
    The api_key, if supplied, is persisted but never returned in responses.
    """
    config = store.load()
    if body.provider_id not in config.providers:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{body.provider_id}' not found.",
        )

    provider_cfg = config.providers[body.provider_id]

    if body.enabled is not None:
        provider_cfg.enabled = body.enabled
    if body.model is not None:
        provider_cfg.model = body.model
    if body.base_url is not None:
        provider_cfg.base_url = body.base_url
    if body.api_key is not None:
        provider_cfg.secrets.api_key = body.api_key

    store.save(config)
    return ProviderConfigPublic.from_config(provider_cfg)


@router.put("/provider/active")
def set_active_provider(
    body: SetActiveProviderRequest,
    store: ConfigStoreDep,
) -> RuntimeProviderConfigPublic:
    """
    Switch the active (and optionally fallback) provider.

    Both provider IDs must be registered in the config.
    """
    config = store.load()

    if body.active_provider not in config.providers:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot set active provider: '{body.active_provider}' is not configured.",
        )
    if body.fallback_provider is not None and body.fallback_provider not in config.providers:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot set fallback provider: '{body.fallback_provider}' is not configured.",
        )

    config.active_provider = body.active_provider
    if body.fallback_provider is not None:
        config.fallback_provider = body.fallback_provider

    store.save(config)
    return RuntimeProviderConfigPublic.from_config(config)


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResponse)
def test_provider_connection(
    provider_id: ProviderId,
    store: ConfigStoreDep,
    registry: ProviderRegistryDep,
) -> ProviderTestResponse:
    """Test connection for a specific provider using current configuration."""
    config = store.load()
    if provider_id not in config.providers:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_id}' not found.",
        )

    provider_cfg = config.providers[provider_id]

    try:
        provider = registry.get(provider_id, provider_cfg)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = provider.test_connection(provider_cfg)

    return ProviderTestResponse(
        provider_id=provider_id,
        success=result.success,
        latency_ms=result.latency_ms,
        error=result.error,
    )

