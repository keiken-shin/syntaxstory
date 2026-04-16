from collections.abc import Callable

from app.llm.providers.base import LLMProvider, ProviderCapabilities, ProviderId
from app.llm.providers.stub import StubProvider
from app.llm.providers.ollama import OllamaProvider

from app.config.models import ProviderConfig
ProviderFactory = Callable[[ProviderConfig], LLMProvider]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[ProviderId, ProviderFactory] = {}

    def register(self, provider_id: ProviderId, factory: ProviderFactory) -> None:
        self._providers[provider_id] = factory

    def get(self, provider_id: ProviderId, config: ProviderConfig) -> LLMProvider:
        if provider_id not in self._providers:
            raise KeyError(f"Provider not registered: {provider_id}")
        return self._providers[provider_id](config)

    def list_registered(self) -> list[ProviderId]:
        return sorted(self._providers.keys(), key=lambda item: item.value)


def build_default_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(
        ProviderId.GEMINI,
        lambda config: StubProvider(
            provider_id=ProviderId.GEMINI,
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_json_mode=True,
            ),
        ),
    )
    registry.register(
        ProviderId.OPENAI,
        lambda config: StubProvider(
            provider_id=ProviderId.OPENAI,
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_tools=True,
                supports_json_mode=True,
            ),
        ),
    )
    registry.register(
        ProviderId.ANTHROPIC,
        lambda config: StubProvider(
            provider_id=ProviderId.ANTHROPIC,
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_tools=True,
            ),
        ),
    )
    registry.register(
        ProviderId.OLLAMA,
        lambda config: OllamaProvider(config)
    )

    return registry
