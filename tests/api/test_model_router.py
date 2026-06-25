from unittest.mock import patch

import pytest

from api.model_router import ModelRouter
from api.models.anthropic import Message, MessagesRequest, TokenCountRequest
from config.settings import Settings


@pytest.fixture
def settings():
    settings = Settings()
    settings.model = "opencode/fallback-model"
    settings.model_opus = None
    settings.model_sonnet = None
    settings.model_haiku = None
    settings.enable_model_thinking = True
    settings.enable_opus_thinking = None
    settings.enable_sonnet_thinking = None
    settings.enable_haiku_thinking = None
    return settings


def test_model_router_resolves_default_model(settings):
    resolved = ModelRouter(settings).resolve("claude-3-opus")

    assert resolved.original_model == "claude-3-opus"
    assert resolved.provider_id == "opencode"
    assert resolved.provider_model == "fallback-model"
    assert resolved.provider_model_ref == "opencode/fallback-model"
    assert resolved.thinking_enabled is True


def test_model_router_applies_opus_override(settings):
    settings.model_opus = "opencode_go/deepseek/deepseek-r1"

    request = MessagesRequest(
        model="claude-opus-4-20250514",
        max_tokens=100,
        messages=[Message(role="user", content="hello")],
    )
    routed = ModelRouter(settings).resolve_messages_request(request)

    assert routed.request.model == "deepseek/deepseek-r1"
    assert routed.resolved.provider_model_ref == "opencode_go/deepseek/deepseek-r1"
    assert routed.resolved.original_model == "claude-opus-4-20250514"
    assert routed.resolved.thinking_enabled is True
    assert request.model == "claude-opus-4-20250514"


def test_model_router_resolves_per_model_thinking(settings):
    settings.enable_model_thinking = False
    settings.enable_opus_thinking = True
    settings.enable_haiku_thinking = False

    router = ModelRouter(settings)

    assert router.resolve("claude-opus-4-20250514").thinking_enabled is True
    assert router.resolve("claude-sonnet-4-20250514").thinking_enabled is False
    assert router.resolve("claude-3-haiku-20240307").thinking_enabled is False
    assert router.resolve("claude-2.1").thinking_enabled is False


def test_model_router_applies_haiku_override(settings):
    settings.model_haiku = "opencode/qwen2.5-7b"

    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "qwen2.5-7b"
    assert routed.resolved.provider_model_ref == "opencode/qwen2.5-7b"


def test_model_router_applies_sonnet_override(settings):
    settings.model_sonnet = "opencode/meta/llama-3.3-70b-instruct"

    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "meta/llama-3.3-70b-instruct"
    assert routed.resolved.provider_model_ref == "opencode/meta/llama-3.3-70b-instruct"


def test_model_router_routes_prefixed_provider_model_directly(settings):
    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="opencode/deepseek-chat",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "deepseek-chat"
    assert routed.resolved.original_model == "opencode/deepseek-chat"
    assert routed.resolved.provider_id == "opencode"
    assert routed.resolved.provider_model == "deepseek-chat"
    assert routed.resolved.provider_model_ref == "opencode/deepseek-chat"


def test_model_router_routes_opencode_go_provider_model_directly(settings):
    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="opencode_go/DeepSeek-V4-Pro",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "DeepSeek-V4-Pro"
    assert routed.resolved.provider_id == "opencode_go"
    assert routed.resolved.provider_model == "DeepSeek-V4-Pro"
    assert routed.resolved.provider_model_ref == "opencode_go/DeepSeek-V4-Pro"


def test_model_router_routes_gateway_encoded_provider_model_directly(settings):
    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="anthropic/opencode/deepseek-ai/deepseek-v4-pro",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "deepseek-ai/deepseek-v4-pro"
    assert (
        routed.resolved.original_model
        == "anthropic/opencode/deepseek-ai/deepseek-v4-pro"
    )
    assert routed.resolved.provider_id == "opencode"
    assert routed.resolved.provider_model == "deepseek-ai/deepseek-v4-pro"
    assert (
        routed.resolved.provider_model_ref
        == "anthropic/opencode/deepseek-ai/deepseek-v4-pro"
    )


def test_model_router_routes_no_thinking_gateway_model_directly(settings):
    settings.enable_model_thinking = True

    routed = ModelRouter(settings).resolve_messages_request(
        MessagesRequest(
            model="claude-3-freecc-no-thinking/opencode/deepseek-ai/deepseek-v4-pro",
            max_tokens=100,
            messages=[Message(role="user", content="hello")],
        )
    )

    assert routed.request.model == "deepseek-ai/deepseek-v4-pro"
    assert (
        routed.resolved.original_model
        == "claude-3-freecc-no-thinking/opencode/deepseek-ai/deepseek-v4-pro"
    )
    assert routed.resolved.provider_id == "opencode"
    assert routed.resolved.provider_model == "deepseek-ai/deepseek-v4-pro"
    assert routed.resolved.thinking_enabled is False


def test_model_router_direct_prefixed_model_uses_provider_model_for_thinking(settings):
    settings.enable_model_thinking = False
    settings.enable_opus_thinking = True

    resolved = ModelRouter(settings).resolve("opencode_go/anthropic/claude-opus-4")

    assert resolved.provider_id == "opencode_go"
    assert resolved.provider_model == "anthropic/claude-opus-4"
    assert resolved.thinking_enabled is True


def test_model_router_routes_token_count_request(settings):
    settings.model_haiku = "opencode/qwen2.5-7b"

    request = TokenCountRequest(
        model="claude-3-haiku-20240307",
        messages=[Message(role="user", content="hello")],
    )
    routed = ModelRouter(settings).resolve_token_count_request(request)

    assert routed.request.model == "qwen2.5-7b"
    assert request.model == "claude-3-haiku-20240307"


def test_model_router_logs_mapping(settings):
    with patch("api.model_router.logger.debug") as mock_log:
        ModelRouter(settings).resolve("claude-2.1")

    mock_log.assert_called()
    args = mock_log.call_args[0]
    assert "MODEL MAPPING" in args[0]
    assert args[1] == "claude-2.1"
    assert args[2] == "fallback-model"
