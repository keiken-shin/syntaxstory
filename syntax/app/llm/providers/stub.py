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
        content = f"[{self.provider_id}] provider stub response for: {request.prompt}"
        
        # If the prompt explicitly asks for yaml output structure, return a valid fake wrapper
        if "```yaml" in request.prompt:
            if "what is the best order to explain these abstractions" in request.prompt:
                # Stub out Order Chapters yaml - just return 0, 1 for basic testing
                content = '''```yaml\n- 0 # Stub Abstraction\n```'''
            elif "relationships:" in request.prompt:
                # Stub out relationships analysis yaml
                content = '''```yaml\nsummary: |\n  Test stub summary.\nrelationships:\n  - from_abstraction: 0\n    to_abstraction: 0\n    label: "Uses"\n```'''
            elif "- name:" in request.prompt:
                # Stub out Identify Abstractions yaml
                content = '''```yaml\n- name: "Stub Abstraction"\n  description: "A stub."\n  file_indices:\n    - 0\n```'''
            else:
                # Generic yaml stub
                content = '''```yaml\nstub: true\n```'''
                
        return GenerateResponse(
            provider=self.provider_id,
            content=content,
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

