from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


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


class LLMProvider(Protocol):
    provider_id: ProviderId
    capabilities: ProviderCapabilities

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        ...
