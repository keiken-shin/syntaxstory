from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.config.models import ProviderConfig


class ProviderId(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ProviderCapabilities(BaseModel):
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json_mode: bool = False


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None


class GenerateResponse(BaseModel):
    provider: ProviderId
    content: str


class ConnectionTestResult(BaseModel):
    """Result of a provider connectivity probe."""

    success: bool
    latency_ms: float | None = None
    error: str | None = None


class LLMProvider(Protocol):
    provider_id: ProviderId
    capabilities: ProviderCapabilities

    def generate(self, request: GenerateRequest) -> GenerateResponse: ...

    def test_connection(self, config: "ProviderConfig") -> ConnectionTestResult: ...

