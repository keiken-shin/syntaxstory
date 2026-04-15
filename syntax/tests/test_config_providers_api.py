from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config.models import RuntimeProviderConfig
from app.config.store import ProviderConfigStore
from app.llm.providers.base import ProviderId
from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """TestClient with an isolated, default-seeded config store."""
    config_path = tmp_path / "provider_config.json"
    store = ProviderConfigStore(str(config_path))
    store.save(RuntimeProviderConfig.default())

    app.state.config_store = store
    return TestClient(app)


def test_list_providers_returns_all_providers(client: TestClient) -> None:
    response = client.get("/api/config/providers")

    assert response.status_code == 200
    body = response.json()
    provider_ids = {p["provider_id"] for p in body["providers"]}
    assert provider_ids == {"gemini", "openai", "anthropic", "ollama"}


def test_list_providers_redacts_api_key(client: TestClient) -> None:
    """api_key must never appear in the response; only has_api_key bool."""
    response = client.get("/api/config/providers")

    body = response.json()
    for provider in body["providers"]:
        assert "api_key" not in provider["secrets"]
        assert "has_api_key" in provider["secrets"]


def test_list_providers_has_api_key_false_by_default(client: TestClient) -> None:
    response = client.get("/api/config/providers")

    body = response.json()
    for provider in body["providers"]:
        assert provider["secrets"]["has_api_key"] is False


def test_list_providers_active_provider_is_gemini_by_default(client: TestClient) -> None:
    response = client.get("/api/config/providers")

    assert response.json()["active_provider"] == "gemini"


def test_get_provider_returns_correct_provider(client: TestClient) -> None:
    response = client.get("/api/config/providers/openai")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == "openai"
    assert body["model"] == "gpt-4o-mini"


def test_get_provider_returns_404_for_unknown(client: TestClient) -> None:
    response = client.get("/api/config/providers/unknown_provider")

    assert response.status_code == 422  # Pydantic enum validation rejects unknown value


def test_get_provider_redacts_secrets(client: TestClient) -> None:
    response = client.get("/api/config/providers/gemini")

    body = response.json()
    assert "api_key" not in body["secrets"]
    assert body["secrets"]["has_api_key"] is False


def test_patch_provider_updates_model(client: TestClient) -> None:
    response = client.patch(
        "/api/config/provider",
        json={"provider_id": "openai", "model": "gpt-4o"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-4o"


def test_patch_provider_persists_api_key_but_does_not_return_it(
    client: TestClient,
) -> None:
    response = client.patch(
        "/api/config/provider",
        json={"provider_id": "gemini", "api_key": "secret-key-value"},
    )

    assert response.status_code == 200
    body = response.json()
    # Key value must not appear in the response
    assert "secret-key-value" not in str(body)
    # But has_api_key should now be True
    assert body["secrets"]["has_api_key"] is True


def test_patch_provider_key_persisted_in_store(tmp_path: Path) -> None:
    """Verify the api_key is actually written to the underlying store."""
    config_path = tmp_path / "provider_config.json"
    store = ProviderConfigStore(str(config_path))
    store.save(RuntimeProviderConfig.default())
    app.state.config_store = store

    TestClient(app).patch(
        "/api/config/provider",
        json={"provider_id": "gemini", "api_key": "my-persisted-key"},
    )

    saved = store.load()
    assert saved.providers[ProviderId.GEMINI].secrets.api_key == "my-persisted-key"


def test_patch_provider_returns_404_for_unconfigured_provider(
    client: TestClient,
) -> None:
    # "ollama" is registered but let's pass a completely invalid enum value
    response = client.patch(
        "/api/config/provider",
        json={"provider_id": "nonexistent"},
    )
    assert response.status_code == 422


def test_patch_provider_partial_update_leaves_other_fields_unchanged(
    client: TestClient,
) -> None:
    # Only update base_url; model should remain untouched
    original = client.get("/api/config/providers/anthropic").json()

    client.patch(
        "/api/config/provider",
        json={"provider_id": "anthropic", "base_url": "https://custom.anthropic.com"},
    )

    updated = client.get("/api/config/providers/anthropic").json()
    assert updated["base_url"] == "https://custom.anthropic.com"
    assert updated["model"] == original["model"]


def test_set_active_provider_switches_active(client: TestClient) -> None:
    response = client.put(
        "/api/config/provider/active",
        json={"active_provider": "ollama"},
    )

    assert response.status_code == 200
    assert response.json()["active_provider"] == "ollama"


def test_set_active_provider_with_fallback(client: TestClient) -> None:
    response = client.put(
        "/api/config/provider/active",
        json={"active_provider": "anthropic", "fallback_provider": "gemini"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_provider"] == "anthropic"
    assert body["fallback_provider"] == "gemini"


def test_set_active_provider_persists(tmp_path: Path) -> None:
    config_path = tmp_path / "provider_config.json"
    store = ProviderConfigStore(str(config_path))
    store.save(RuntimeProviderConfig.default())
    app.state.config_store = store

    TestClient(app).put(
        "/api/config/provider/active",
        json={"active_provider": "openai"},
    )

    assert store.load().active_provider == ProviderId.OPENAI


def test_set_active_provider_rejects_invalid_provider(client: TestClient) -> None:
    response = client.put(
        "/api/config/provider/active",
        json={"active_provider": "does_not_exist"},
    )
    assert response.status_code == 422


def test_test_provider_connection_success(client: TestClient) -> None:
    # Gemini is enabled by default in DefaultConfigStore
    response = client.post("/api/config/providers/gemini/test")
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "gemini"
    assert data["success"] is True
    assert "latency_ms" in data
    assert data["error"] is None


def test_test_provider_connection_disabled(client: TestClient) -> None:
    # Disable it first
    client.patch("/api/config/provider", json={"provider_id": "gemini", "enabled": False})
    response = client.post("/api/config/providers/gemini/test")
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "gemini"
    assert data["success"] is False
    assert data["error"] == "Provider 'gemini' is disabled."


def test_test_provider_connection_not_found(client: TestClient) -> None:
    response = client.post("/api/config/providers/unknown_provider/test")
    assert response.status_code == 422  # validation error since it's an enum, or 404

