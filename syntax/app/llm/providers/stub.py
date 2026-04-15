import time

from app.llm.providers.base import (
    ConnectionTestResult,
    GenerateRequest,
    GenerateResponse,
    ProviderCapabilities,
    ProviderId,
)

if True:  # avoid circular import at runtime; ProviderConfig only needed for type
    from app.config.models import ProviderConfig


class StubProvider:
    def __init__(
        self,
        provider_id: ProviderId,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.capabilities = capabilities or ProviderCapabilities()

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(
            provider=self.provider_id,
            content=f"[{self.provider_id}] provider stub response for: {request.prompt}",
        )

    def test_connection(self, config: "ProviderConfig") -> ConnectionTestResult:
        """Simulate a connectivity probe. Returns failure if provider is disabled."""
        start = time.perf_counter()
        if not config.enabled:
            return ConnectionTestResult(
                success=False,
                latency_ms=None,
                error=f"Provider '{self.provider_id}' is disabled.",
            )
        latency_ms = (time.perf_counter() - start) * 1000
        return ConnectionTestResult(success=True, latency_ms=round(latency_ms, 3))

