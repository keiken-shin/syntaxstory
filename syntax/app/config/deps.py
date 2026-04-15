from typing import Annotated

from fastapi import Depends, Request

from app.config.store import ProviderConfigStore


def get_config_store(request: Request) -> ProviderConfigStore:
    return request.app.state.config_store


ConfigStoreDep = Annotated[ProviderConfigStore, Depends(get_config_store)]
