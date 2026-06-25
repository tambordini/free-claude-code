from fastapi.testclient import TestClient

from api.app import create_app
from api.dependencies import get_settings
from config.settings import Settings
from providers.model_listing import ProviderModelInfo
from providers.registry import ProviderRegistry


def _settings(
    *,
    model: str = "opencode/deepseek-chat",
    model_opus: str | None = "opencode_go/anthropic/claude-opus",
    model_haiku: str | None = "opencode/deepseek-chat",
) -> Settings:
    return Settings.model_construct(
        model=model,
        model_opus=model_opus,
        model_sonnet=None,
        model_haiku=model_haiku,
        anthropic_auth_token="",
    )


def test_models_list_includes_configured_refs_cached_provider_models_and_aliases():
    app = create_app(lifespan_enabled=False)
    settings = _settings()
    registry = ProviderRegistry()
    registry.cache_model_ids("opencode", {"deepseek-chat"})
    registry.cache_model_ids("opencode_go", {"meta/llama-3.3", "anthropic/claude-opus"})
    app.state.provider_registry = registry
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).get("/v1/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["data"]]

    assert ids[:6] == [
        "anthropic/opencode/deepseek-chat",
        "claude-3-freecc-no-thinking/opencode/deepseek-chat",
        "anthropic/opencode_go/anthropic/claude-opus",
        "claude-3-freecc-no-thinking/opencode_go/anthropic/claude-opus",
        "anthropic/opencode_go/meta/llama-3.3",
        "claude-3-freecc-no-thinking/opencode_go/meta/llama-3.3",
    ]
    assert ids.count("anthropic/opencode/deepseek-chat") == 1
    assert ids.count("claude-3-freecc-no-thinking/opencode/deepseek-chat") == 1
    assert ids.count("anthropic/opencode_go/anthropic/claude-opus") == 1
    assert (
        ids.count("claude-3-freecc-no-thinking/opencode_go/anthropic/claude-opus") == 1
    )
    display_names = {item["id"]: item["display_name"] for item in data["data"]}
    assert (
        display_names["anthropic/opencode_go/meta/llama-3.3"]
        == "opencode_go/meta/llama-3.3"
    )
    assert (
        display_names["claude-3-freecc-no-thinking/opencode_go/meta/llama-3.3"]
        == "opencode_go/meta/llama-3.3 (no thinking)"
    )
    assert "claude-sonnet-4-20250514" in ids
    assert data["first_id"] == ids[0]
    assert data["last_id"] == ids[-1]
    assert data["has_more"] is False


def test_models_list_uses_thinking_metadata_for_cached_models():
    app = create_app(lifespan_enabled=False)
    settings = _settings(model_opus=None)
    registry = ProviderRegistry()
    registry.cache_model_ids("opencode", {"deepseek-chat"})
    registry.cache_model_infos(
        "opencode_go",
        {
            ProviderModelInfo("reasoning-model", supports_thinking=True),
            ProviderModelInfo("plain-model", supports_thinking=False),
        },
    )
    app.state.provider_registry = registry
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).get("/v1/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert "anthropic/opencode_go/reasoning-model" in ids
    assert "claude-3-freecc-no-thinking/opencode_go/reasoning-model" in ids
    assert "anthropic/opencode_go/plain-model" not in ids
    assert "claude-3-freecc-no-thinking/opencode_go/plain-model" in ids


def test_models_list_uses_cached_metadata_for_configured_opencode_go_refs():
    app = create_app(lifespan_enabled=False)
    settings = _settings(
        model="opencode_go/plain-model",
        model_opus=None,
        model_haiku=None,
    )
    registry = ProviderRegistry()
    registry.cache_model_infos(
        "opencode_go",
        {ProviderModelInfo("plain-model", supports_thinking=False)},
    )
    app.state.provider_registry = registry
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).get("/v1/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert "anthropic/opencode_go/plain-model" not in ids
    assert ids[0] == "claude-3-freecc-no-thinking/opencode_go/plain-model"


def test_models_list_includes_cached_opencode_go_models():
    app = create_app(lifespan_enabled=False)
    settings = _settings(
        model="opencode_go/DeepSeek-V4-Pro",
        model_opus=None,
        model_haiku=None,
    )
    registry = ProviderRegistry()
    registry.cache_model_ids("opencode_go", {"DeepSeek-V4-Pro", "MiniMax-M2.7"})
    app.state.provider_registry = registry
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).get("/v1/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert "anthropic/opencode_go/DeepSeek-V4-Pro" in ids
    assert "claude-3-freecc-no-thinking/opencode_go/DeepSeek-V4-Pro" in ids
    assert "anthropic/opencode_go/MiniMax-M2.7" in ids
    assert "claude-3-freecc-no-thinking/opencode_go/MiniMax-M2.7" in ids


def test_models_list_works_without_provider_registry():
    app = create_app(lifespan_enabled=False)
    settings = _settings()
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).get("/v1/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids[:4] == [
        "anthropic/opencode/deepseek-chat",
        "claude-3-freecc-no-thinking/opencode/deepseek-chat",
        "anthropic/opencode_go/anthropic/claude-opus",
        "claude-3-freecc-no-thinking/opencode_go/anthropic/claude-opus",
    ]
    assert "claude-sonnet-4-20250514" in ids
