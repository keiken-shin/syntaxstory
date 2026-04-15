from typing import Annotated

from fastapi import Depends, Request

from app.llm.provider_registry import ProviderRegistry


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry


ProviderRegistryDep = Annotated[ProviderRegistry, Depends(get_provider_registry)]
