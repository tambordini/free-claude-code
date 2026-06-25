"""Tests for OpenCode vision model mapping."""

import pytest

from providers.model_listing import ProviderModelInfo


def test_vision_models_defined() -> None:
    from providers.opencode.client import _VISION_MODELS

    assert len(_VISION_MODELS) > 0
    assert "mimo-v2.5-free" in _VISION_MODELS


def test_vision_fallback_defined() -> None:
    from providers.opencode.client import _VISION_MODELS, _VISION_FALLBACK

    for non_vision_model, vision_model in _VISION_FALLBACK.items():
        assert non_vision_model not in _VISION_MODELS
        assert vision_model in _VISION_MODELS


def test_list_model_infos_signature() -> None:
    """At minimum, verify OpenCodeProvider has list_model_infos."""
    from providers.opencode.client import OpenCodeProvider

    assert hasattr(OpenCodeProvider, "list_model_infos")
