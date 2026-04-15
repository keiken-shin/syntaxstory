from app.llm.providers.base import (
    GenerateRequest,
    GenerateResponse,
    ProviderCapabilities,
    ProviderId,
)


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
