"""Tests for ProviderModelInfo data model."""

from providers.model_listing import ProviderModelInfo


def test_supports_vision_defaults_to_none() -> None:
    info = ProviderModelInfo(model_id="test-model")
    assert info.supports_vision is None


def test_supports_vision_can_be_set() -> None:
    info = ProviderModelInfo(model_id="test-model", supports_vision=True)
    assert info.supports_vision is True


def test_supports_vision_explicit_false() -> None:
    info = ProviderModelInfo(model_id="test-model", supports_vision=False)
    assert info.supports_vision is False
