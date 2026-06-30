"""Tests for vision fallback detection and message rewriting."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

import pytest

from api.handlers.messages import (
    MessagesHandler,
    _has_image_content,
    _replace_images_with_text,
)
from api.model_router import ResolvedModel, RoutedMessagesRequest
from api.models.anthropic import (
    ContentBlockImage,
    ContentBlockText,
    Message,
    MessagesRequest,
)
from config.settings import Settings
from config.vision import _VISION_MODELS
from providers.base import BaseProvider, ProviderConfig


class _FakeVisionProvider(BaseProvider):
    """A provider that records send_request and stream_response calls."""

    def __init__(self) -> None:
        super().__init__(ProviderConfig(api_key="test"))
        self.send_request_calls: list[tuple[Any, dict[str, Any]]] = []
        self.stream_requests: list[Any] = []
        self._analysis = "a cute puppy sitting on grass"

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset({"test-model"})

    async def send_request(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> str:
        self.send_request_calls.append(
            (request, {"thinking_enabled": thinking_enabled})
        )
        return self._analysis

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        self.stream_requests.append(request)
        yield 'event: message_start\ndata: {"type":"message_start"}\n\n'
        yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'


def _make_routed(
    model: str,
    messages: list[Message],
) -> RoutedMessagesRequest:
    request = MessagesRequest(model=model, messages=messages)
    return RoutedMessagesRequest(
        request=request,
        resolved=ResolvedModel(
            original_model=model,
            provider_id="opencode",
            provider_model=model,
            provider_model_ref=f"opencode/{model}",
            thinking_enabled=False,
        ),
    )


class TestHasImageContent:
    def test_no_images(self) -> None:
        routed = _make_routed(
            "deepseek-v4-flash",
            [Message(role="user", content="just text")],
        )
        assert _has_image_content(routed.request) is False

    def test_with_images(self) -> None:
        routed = _make_routed(
            "deepseek-v4-flash",
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="what is this?"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        assert _has_image_content(routed.request) is True


class TestReplaceImagesWithText:
    def test_replaces_all_images(self) -> None:
        request = MessagesRequest(
            model="deepseek-v4-flash",
            messages=[
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="hello"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                        ContentBlockText(type="text", text="world"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": "xyz",
                            },
                        ),
                    ],
                ),
            ],
        )
        rewritten = _replace_images_with_text(request, "a dog")
        content = rewritten.messages[0].content
        assert isinstance(content, list)
        texts = [b for b in content if isinstance(b, ContentBlockText)]
        images = [b for b in content if getattr(b, "type", None) == "image"]
        assert len(texts) == 4
        assert images == []
        assert texts[0].text == "hello"
        assert texts[1].text == "[Image: a dog]"
        assert texts[2].text == "world"
        assert texts[3].text == "[Image: a dog]"


class TestApplyVisionFallback:
    @pytest.mark.asyncio
    async def test_no_images_passthrough(self) -> None:
        """Request without images should pass through unchanged."""
        handler = MessagesHandler(
            Settings(), provider_getter=lambda _: _FakeVisionProvider()
        )
        routed = _make_routed(
            "deepseek-v4-flash",
            [Message(role="user", content="hello")],
        )
        result = await handler._apply_vision_fallback(routed)
        assert result is routed  # unchanged

    @pytest.mark.asyncio
    async def test_model_already_vision(self) -> None:
        """Request to a vision-capable model should pass through unchanged."""
        vision_model = next(iter(_VISION_MODELS))
        handler = MessagesHandler(
            Settings(), provider_getter=lambda _: _FakeVisionProvider()
        )
        routed = _make_routed(
            vision_model,
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="what is this?"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        result = await handler._apply_vision_fallback(routed)
        assert result is routed  # unchanged

    @pytest.mark.asyncio
    async def test_no_fallback_configured(self) -> None:
        """Request with images but no fallback for this model should pass through."""
        handler = MessagesHandler(
            Settings(), provider_getter=lambda _: _FakeVisionProvider()
        )
        routed = _make_routed(
            "unknown-model",
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="hello"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        result = await handler._apply_vision_fallback(routed)
        assert result is routed  # unchanged

    @pytest.mark.asyncio
    async def test_sends_to_vision_model(self) -> None:
        """Request with images to non-vision model triggers fallback."""
        provider = _FakeVisionProvider()
        handler = MessagesHandler(Settings(), provider_getter=lambda _: provider)

        routed = _make_routed(
            "deepseek-v4-flash-free",
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="what is this?"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        result = await handler._apply_vision_fallback(routed)

        # The request should be rewritten (not the same object).
        assert result is not routed

        # The fallback provider should have been called with a vision request.
        assert len(provider.send_request_calls) == 1
        vision_req, _ = provider.send_request_calls[0]
        assert vision_req.model == "mimo-v2.5-free"
        assert vision_req.stream is False

        # The rewritten request should have images replaced with text.
        rewritten_content = result.request.messages[0].content
        assert isinstance(rewritten_content, list)
        # No image blocks should remain.
        image_blocks = [
            b for b in rewritten_content if getattr(b, "type", None) == "image"
        ]
        assert image_blocks == []
        # The first block is the original text, preserved.
        assert isinstance(rewritten_content[0], ContentBlockText)
        assert rewritten_content[0].text == "what is this?"
        # The second block should be the analysis text.
        assert isinstance(rewritten_content[1], ContentBlockText)
        assert "puppy" in rewritten_content[1].text

    @pytest.mark.asyncio
    async def test_fallback_failure_returns_original(self) -> None:
        """When the fallback provider call fails, the original request is unchanged."""
        provider = _FakeVisionProvider()
        provider._analysis = "some text"  # will be unused; we'll make send_request fail

        handler = MessagesHandler(Settings(), provider_getter=lambda _: provider)

        routed = _make_routed(
            "deepseek-v4-flash",
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        # Override send_request to raise
        with patch.object(
            provider, "send_request", side_effect=RuntimeError("API timeout")
        ):
            result = await handler._apply_vision_fallback(routed)
        assert result is routed  # unchanged on failure

    @pytest.mark.asyncio
    async def test_fallback_empty_analysis_returns_original(self) -> None:
        """When the fallback provider returns empty string, the original is unchanged."""
        provider = _FakeVisionProvider()
        provider._analysis = ""
        handler = MessagesHandler(Settings(), provider_getter=lambda _: provider)

        routed = _make_routed(
            "deepseek-v4-flash",
            [
                Message(
                    role="user",
                    content=[
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )
        result = await handler._apply_vision_fallback(routed)
        assert result is routed  # unchanged

    @pytest.mark.asyncio
    async def test_e2e_via_handler_create(self) -> None:
        """Full integration: create() triggers vision fallback before provider stream."""
        provider = _FakeVisionProvider()
        handler = MessagesHandler(
            Settings(),
            provider_getter=lambda _: provider,
        )
        request = MessagesRequest(
            model="opencode/deepseek-v4-flash",
            messages=[
                Message(
                    role="user",
                    content=[
                        ContentBlockText(type="text", text="describe it"),
                        ContentBlockImage(
                            type="image",
                            source={
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abc",
                            },
                        ),
                    ],
                ),
            ],
        )

        from fastapi.responses import StreamingResponse

        response = await handler.create(request)
        assert isinstance(response, StreamingResponse)

        # Verify the fallback provider was called.
        assert len(provider.send_request_calls) == 1

        # Consume the stream so stream_response is actually called.
        body_parts: list[str] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                body_parts.append(chunk.decode("utf-8"))
            else:
                body_parts.append(str(chunk))

        # Verify the streamed request has images replaced.
        assert len(provider.stream_requests) == 1
        content = provider.stream_requests[0].messages[0].content
        assert isinstance(content, list)
        assert isinstance(content[1], ContentBlockText)
        assert content[1].text == "[Image: a cute puppy sitting on grass]"
        # Verify the stream actually produced events.
        assert "message_start" in "".join(body_parts)
