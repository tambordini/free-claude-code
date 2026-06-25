"""Tests for vision fallback detection and message rewriting."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.model_router import ResolvedModel, RoutedMessagesRequest
from api.models.anthropic import Message, MessagesRequest
from api.request_pipeline import (
    ApiRequestPipeline,
    _has_image_content,
    _replace_images_with_text,
)


def _make_msg(content: list) -> MessagesRequest:
    return MessagesRequest(
        model="test-model",
        messages=[Message(role="user", content=content)],
    )


def test_has_image_content_true() -> None:
    """Request with an image block returns True."""
    req = _make_msg(
        [
            {"type": "text", "text": "hello"},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": "abc"},
            },
        ]
    )
    assert _has_image_content(req) is True


def test_has_image_content_false() -> None:
    """Request with only text returns False."""
    req = _make_msg(
        [
            {"type": "text", "text": "hello"},
        ]
    )
    assert _has_image_content(req) is False


def test_has_image_content_empty() -> None:
    """Request with empty content returns False."""
    req = _make_msg([])
    assert _has_image_content(req) is False


def test_replace_images_with_text() -> None:
    """Image block is replaced with text block containing analysis."""
    req = _make_msg(
        [
            {"type": "text", "text": "what is this?"},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": "abc"},
            },
        ]
    )
    analysis = "A cat sitting on a keyboard"
    rewritten = _replace_images_with_text(req, analysis)

    msg_content = rewritten.messages[0].content
    assert len(msg_content) == 2
    assert msg_content[0].type == "text"
    assert msg_content[0].text == "what is this?"
    assert msg_content[1].type == "text"
    assert "[Image: A cat sitting on a keyboard]" in msg_content[1].text


def test_replace_images_with_text_multiple_images() -> None:
    """Multiple image blocks are each replaced with text."""
    req = _make_msg(
        [
            {
                "type": "image",
                "source": {"type": "url", "url": "http://example.com/a.png"},
            },
            {
                "type": "image",
                "source": {"type": "url", "url": "http://example.com/b.png"},
            },
        ]
    )
    rewritten = _replace_images_with_text(req, "two images")
    text_blocks = [b for b in rewritten.messages[0].content if b.type == "text"]
    assert len(text_blocks) == 2
    assert all("two images" in b.text for b in text_blocks)


def test_vision_fallback_maps_opencode_go() -> None:
    """opencode_go provider model deepseek-v4-flash maps to mimo-v2.5."""
    from api.request_pipeline import _VISION_FALLBACK, _VISION_MODELS

    assert "deepseek-v4-flash" in _VISION_FALLBACK
    assert _VISION_FALLBACK["deepseek-v4-flash"] == "mimo-v2.5"
    assert "mimo-v2.5" in _VISION_MODELS


def test_replace_images_with_text_preserves_original() -> None:
    """Original request object is not mutated."""
    req = _make_msg(
        [
            {
                "type": "image",
                "source": {"type": "url", "url": "http://example.com/img.png"},
            },
        ]
    )
    _replace_images_with_text(req, "analysis")
    assert len(req.messages[0].content) == 1
    assert req.messages[0].content[0].type == "image"


@pytest.mark.asyncio
async def test_vision_fallback_no_images_passthrough() -> None:
    """Request without images should pass through unchanged."""
    from config.settings import Settings

    settings = Settings.model_construct(opencode_api_key="test")
    request = MessagesRequest(
        model="opencode/deepseek-v4-flash-free",
        messages=[Message(role="user", content="hello")],
    )
    routed = RoutedMessagesRequest(
        request=request,
        resolved=ResolvedModel(
            original_model="opencode/deepseek-v4-flash-free",
            provider_id="opencode",
            provider_model="deepseek-v4-flash-free",
            provider_model_ref="opencode/deepseek-v4-flash-free",
            thinking_enabled=False,
        ),
    )

    pipeline = ApiRequestPipeline(
        settings,
        provider_getter=MagicMock(),
    )
    result = await pipeline._apply_vision_fallback(routed)
    assert result is routed  # unchanged


@pytest.mark.asyncio
async def test_vision_fallback_model_already_vision() -> None:
    """Request to a vision-capable model should pass through unchanged."""
    from providers.opencode.client import _VISION_MODELS

    vision_model = next(iter(_VISION_MODELS))
    request = MessagesRequest(
        model=vision_model,
        messages=[
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "what is this?"},
                    {
                        "type": "image",
                        "source": {"type": "url", "url": "http://example.com/img.png"},
                    },
                ],
            )
        ],
    )
    routed = RoutedMessagesRequest(
        request=request,
        resolved=ResolvedModel(
            original_model=vision_model,
            provider_id="opencode",
            provider_model=vision_model,
            provider_model_ref=f"opencode/{vision_model}",
            thinking_enabled=False,
        ),
    )

    settings = MagicMock()
    pipeline = ApiRequestPipeline(
        settings,
        provider_getter=MagicMock(),
    )
    result = await pipeline._apply_vision_fallback(routed)
    assert result is routed  # unchanged


@pytest.mark.asyncio
async def test_vision_fallback_sends_to_vision_model() -> None:
    """Request with images to non-vision model triggers fallback."""
    from config.settings import Settings

    request = MessagesRequest(
        model="opencode/deepseek-v4-flash-free",
        messages=[
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "what's in this image?"},
                    {
                        "type": "image",
                        "source": {"type": "url", "url": "http://example.com/img.png"},
                    },
                ],
            )
        ],
    )
    routed = RoutedMessagesRequest(
        request=request,
        resolved=ResolvedModel(
            original_model="opencode/deepseek-v4-flash-free",
            provider_id="opencode",
            provider_model="deepseek-v4-flash-free",
            provider_model_ref="opencode/deepseek-v4-flash-free",
            thinking_enabled=False,
        ),
    )

    mock_provider = MagicMock()
    mock_provider.send_request = AsyncMock(return_value="A cute puppy")

    settings = Settings.model_construct(
        opencode_api_key="test",
        log_api_error_tracebacks=False,
    )
    pipeline = ApiRequestPipeline(
        settings,
        provider_getter=lambda _: mock_provider,
    )
    result = await pipeline._apply_vision_fallback(routed)

    mock_provider.send_request.assert_awaited_once()

    call_kwargs = mock_provider.send_request.call_args
    vision_req = call_kwargs[0][0]
    assert vision_req.model == "mimo-v2.5-free"
    assert vision_req.stream is False

    assert result is not routed
    rewritten_content = result.request.messages[0].content
    assert len(rewritten_content) == 2
    assert rewritten_content[0].type == "text"
    assert rewritten_content[1].type == "text"
    assert "[Image: A cute puppy]" in rewritten_content[1].text
