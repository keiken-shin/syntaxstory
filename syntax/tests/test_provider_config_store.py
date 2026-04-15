from pathlib import Path

from app.config.models import RuntimeProviderConfig
from app.config.store import ProviderConfigStore
from app.llm.providers.base import ProviderId


def test_store_creates_default_config_if_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "provider_config.json"
    store = ProviderConfigStore(str(config_path))

    config = store.load()

    assert config.active_provider == ProviderId.GEMINI
    assert config_path.exists()


def test_store_persists_and_loads_config(tmp_path: Path) -> None:
    config_path = tmp_path / "provider_config.json"
    store = ProviderConfigStore(str(config_path))
    config = RuntimeProviderConfig.default()
    config.active_provider = ProviderId.OLLAMA
    config.fallback_provider = ProviderId.GEMINI

    store.save(config)
    loaded = store.load()

    assert loaded.active_provider == ProviderId.OLLAMA
    assert loaded.fallback_provider == ProviderId.GEMINI
    assert ProviderId.OPENAI in loaded.providers
