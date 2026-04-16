import time
import requests

from app.llm.providers.base import (
    ConnectionTestResult,
    GenerateRequest,
    GenerateResponse,
    ProviderCapabilities,
    ProviderId,
)

if True:  # avoid circular import
    from app.config.models import ProviderConfig


class OllamaProvider:
    def __init__(self, config: "ProviderConfig") -> None:
        self.provider_id = ProviderId.OLLAMA
        self.capabilities = ProviderCapabilities(supports_json_mode=True)
        self.config = config

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        base_url = self.config.base_url.rstrip("/") if self.config.base_url else "http://localhost:11434"
        url = f"{base_url}/api/generate"
        
        model = request.model or self.config.model or "llama3.2"
        
        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False
        }
        
        # Removed timeout to allow large models (like 26b) sufficient time to generate long chapters
        response = requests.post(url, json=payload, timeout=None)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("response", "")
        
        return GenerateResponse(
            provider=self.provider_id,
            content=content,
        )

    def test_connection(self, config: "ProviderConfig") -> ConnectionTestResult:
        start = time.perf_counter()
        if not config.enabled:
            return ConnectionTestResult(
                success=False,
                latency_ms=None,
                error=f"Provider '{self.provider_id}' is disabled.",
            )
        try:
            base_url = config.base_url.rstrip("/") if config.base_url else "http://localhost:11434"
            url = f"{base_url}/api/tags"
            response = requests.get(url, timeout=5.0)
            response.raise_for_status()
        except Exception as e:
            return ConnectionTestResult(success=False, error=str(e))
            
        latency_ms = (time.perf_counter() - start) * 1000
        return ConnectionTestResult(success=True, latency_ms=round(latency_ms, 3))
