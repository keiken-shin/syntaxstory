import pytest

from app.llm.provider_registry import ProviderRegistry, build_default_provider_registry
from app.llm.providers.base import GenerateRequest, ProviderId
from app.llm.providers.stub import StubProvider


def test_default_registry_registers_all_target_providers() -> None:
    registry = build_default_provider_registry()

    assert registry.list_registered() == [
        ProviderId.ANTHROPIC,
        ProviderId.GEMINI,
        ProviderId.OLLAMA,
        ProviderId.OPENAI,
    ]


def test_registry_returns_provider_instance() -> None:
    registry = build_default_provider_registry()
    provider = registry.get(ProviderId.GEMINI)

    response = provider.generate(GenerateRequest(prompt="hello"))

    assert response.provider == ProviderId.GEMINI
    assert "hello" in response.content


def test_registry_raises_for_unregistered_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError):
        registry.get(ProviderId.OPENAI)


def test_registry_supports_custom_provider_registration() -> None:
    registry = ProviderRegistry()
    registry.register(ProviderId.OLLAMA, lambda: StubProvider(provider_id=ProviderId.OLLAMA))

    provider = registry.get(ProviderId.OLLAMA)

    assert provider.provider_id == ProviderId.OLLAMA
