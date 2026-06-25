"""Smoke config contract tests for opencode-only deployment."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from smoke.conftest import DISABLED_PROVIDER_MODEL, provider_model_params
from smoke.lib.config import SmokeConfig


def _settings(**overrides):
    values = {
        "model": "opencode/deepseek-v4-flash-free",
        "model_opus": None,
        "model_sonnet": None,
        "model_haiku": None,
        "opencode_api_key": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _smoke_config(**overrides) -> SmokeConfig:
    values = {
        "root": Path("."),
        "results_dir": Path(".smoke-results"),
        "live": False,
        "interactive": False,
        "targets": frozenset(),
        "provider_matrix": frozenset(),
        "timeout_s": 45.0,
        "prompt": "Reply with exactly: FCC_SMOKE_PONG",
        "claude_bin": "claude",
        "worker_id": "main",
        "settings": _settings(),
    }
    values.update(overrides)
    return SmokeConfig(**values)


def test_provider_configuration_uses_api_key() -> None:
    config = _smoke_config(
        settings=_settings(opencode_api_key="test-key"),
    )

    assert config.has_provider_configuration("opencode")
    models = config.provider_smoke_models()
    assert models[0].provider == "opencode"
    assert models[0].source == "provider_default"


def test_provider_smoke_collection_uses_disabled_placeholder_when_not_live() -> None:
    config = _smoke_config(live=False, settings=_settings(opencode_api_key="test-key"))

    params = provider_model_params(config)

    assert [param.values[0] for param in params] == [DISABLED_PROVIDER_MODEL]
