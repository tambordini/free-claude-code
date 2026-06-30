"""Claude Messages API product flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from loguru import logger

from api.detection import is_safety_classifier_request
from api.model_router import ModelRouter, RoutedMessagesRequest
from api.models.anthropic import (
    ContentBlockText,
    Message,
    MessagesRequest,
    SystemContent,
)
from api.optimization_handlers import try_optimizations
from api.provider_execution import ProviderExecutionService, TokenCounter
from api.request_errors import require_non_empty_messages, unexpected_http_exception
from api.response_streams import anthropic_sse_streaming_response
from api.web_tools.egress import WebFetchEgressPolicy, web_fetch_allowed_scheme_set
from api.web_tools.request import (
    is_web_server_tool_request,
    openai_chat_upstream_server_tool_error,
)
from api.web_tools.streaming import stream_web_server_tool_response
from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings
from config.vision import _VISION_FALLBACK, _VISION_MODELS
from core.anthropic import get_token_count
from core.trace import trace_event
from providers.base import BaseProvider
from providers.exceptions import InvalidRequestError, ProviderError

# ── Vision fallback helpers ────────────────────────────────────────────────


def _has_image_content(request: Any) -> bool:
    """Return True if any message in the request has image content blocks."""
    for msg in getattr(request, "messages", []):
        content = getattr(msg, "content", None)
        if not isinstance(content, list):
            continue
        for block in content:
            block_type = getattr(block, "type", None) or (
                isinstance(block, dict) and block.get("type")
            )
            if block_type == "image":
                return True
    return False


def _replace_images_with_text(request: Any, analysis: str) -> Any:
    """Return a deep copy of request with all image blocks replaced by text.

    Each image block replaced by ``ContentBlockText("[Image: <analysis>]")``.
    """
    from copy import deepcopy

    new = deepcopy(request)
    for msg in getattr(new, "messages", []):
        content = getattr(msg, "content", None)
        if not isinstance(content, list):
            continue
        for i, block in enumerate(content):
            block_type = getattr(block, "type", None) or (
                isinstance(block, dict) and block.get("type")
            )
            if block_type == "image":
                content[i] = ContentBlockText(type="text", text=f"[Image: {analysis}]")
    return new


ProviderGetter = Callable[[str], BaseProvider]
MessageIntercept = Callable[[RoutedMessagesRequest], object | None]

_OPENAI_CHAT_UPSTREAM_IDS = frozenset(
    provider_id
    for provider_id, descriptor in PROVIDER_CATALOG.items()
    if descriptor.transport_type == "openai_chat"
)


class MessagesHandler:
    """Handle Anthropic-compatible Messages requests."""

    def __init__(
        self,
        settings: Settings,
        provider_getter: ProviderGetter,
        *,
        model_router: ModelRouter | None = None,
        token_counter: TokenCounter = get_token_count,
        provider_execution: ProviderExecutionService | None = None,
    ) -> None:
        self._settings = settings
        self._provider_getter = provider_getter
        self._model_router = model_router or ModelRouter(settings)
        self._token_counter = token_counter
        self._provider_execution = provider_execution or ProviderExecutionService(
            settings,
            provider_getter,
            token_counter=token_counter,
        )
        self._message_intercepts: tuple[MessageIntercept, ...] = (
            self._intercept_web_server_tool,
            self._intercept_local_optimization,
        )

    async def create(self, request_data: MessagesRequest) -> object:
        """Create an Anthropic-compatible message response."""
        try:
            require_non_empty_messages(request_data.messages)
            routed = self._model_router.resolve_messages_request(request_data)
            routed = await self._apply_vision_fallback(routed)
            routed = self._apply_message_routing_policies(routed)
            self._reject_unsupported_server_tools(routed)

            intercepted = self._run_message_intercepts(routed)
            if intercepted is not None:
                return intercepted

            logger.debug("No optimization matched, routing to provider")
            return anthropic_sse_streaming_response(
                self._provider_execution.stream(
                    routed,
                    wire_api="messages",
                    raw_log_label="FULL_PAYLOAD",
                    raw_log_payload=routed.request.model_dump(),
                )
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise unexpected_http_exception(
                self._settings, exc, context="CREATE_MESSAGE_ERROR"
            ) from exc

    def _reject_unsupported_server_tools(self, routed: RoutedMessagesRequest) -> None:
        if routed.resolved.provider_id not in _OPENAI_CHAT_UPSTREAM_IDS:
            return
        tool_err = openai_chat_upstream_server_tool_error(
            routed.request,
            web_tools_enabled=self._settings.enable_web_server_tools,
        )
        if tool_err is not None:
            raise InvalidRequestError(tool_err)

    def _apply_message_routing_policies(
        self, routed: RoutedMessagesRequest
    ) -> RoutedMessagesRequest:
        if not is_safety_classifier_request(routed.request):
            return routed
        changed = routed.resolved.thinking_enabled
        trace_event(
            stage="routing",
            event="api.optimization.safety_classifier_no_thinking",
            source="api",
            model=routed.request.model,
            changed=changed,
        )
        if not changed:
            return routed
        return RoutedMessagesRequest(
            request=routed.request,
            resolved=replace(routed.resolved, thinking_enabled=False),
        )

    async def _apply_vision_fallback(
        self, routed: RoutedMessagesRequest
    ) -> RoutedMessagesRequest:
        """If the request has images but the model doesn't support vision,
        relay to the hardcoded vision fallback model, inject analysis, and
        return the rewritten request. Otherwise return the original unchanged."""
        if not _has_image_content(routed.request):
            return routed

        provider_model = routed.resolved.provider_model

        if provider_model in _VISION_MODELS:
            return routed

        fallback_model = _VISION_FALLBACK.get(provider_model)
        if fallback_model is None:
            logger.debug("No vision fallback configured for model={}", provider_model)
            return routed

        # Collect image blocks from user messages.
        vision_content: list[Any] = []
        for msg in getattr(routed.request, "messages", []):
            content = getattr(msg, "content", None)
            if not isinstance(content, list):
                continue
            for block in content:
                block_type = getattr(block, "type", None) or (
                    isinstance(block, dict) and block.get("type")
                )
                if block_type == "image":
                    vision_content.append(block)

        if not vision_content:
            return routed

        vision_system = (
            "Describe the image(s) in detail, including objects, "
            "text, people, actions, and context."
        )

        vision_request = MessagesRequest(
            model=fallback_model,
            system=[SystemContent(type="text", text=vision_system)],
            messages=[Message(role="user", content=vision_content)],
            stream=False,
        )

        fallback_provider = self._provider_getter(routed.resolved.provider_id)

        try:
            analysis = await fallback_provider.send_request(
                vision_request,
                thinking_enabled=False,
            )
        except Exception as exc:
            logger.warning(
                "Vision fallback failed for model={}: {}", provider_model, exc
            )
            return routed

        if not analysis:
            logger.warning("Vision fallback returned empty analysis")
            return routed

        rewritten_request = _replace_images_with_text(routed.request, analysis)
        logger.info(
            "Vision fallback: {} -> {} ({} chars analysis)",
            provider_model,
            fallback_model,
            len(analysis),
        )
        return RoutedMessagesRequest(
            request=rewritten_request,
            resolved=routed.resolved,
        )

    def _run_message_intercepts(self, routed: RoutedMessagesRequest) -> object | None:
        for intercept in self._message_intercepts:
            result = intercept(routed)
            if result is not None:
                return result
        return None

    def _intercept_web_server_tool(
        self, routed: RoutedMessagesRequest
    ) -> object | None:
        if not self._settings.enable_web_server_tools:
            return None
        if not is_web_server_tool_request(routed.request):
            return None

        input_tokens = self._token_counter(
            routed.request.messages, routed.request.system, routed.request.tools
        )
        trace_event(
            stage="routing",
            event="api.optimization.web_server_tool",
            source="api",
            model=routed.request.model,
        )
        egress = WebFetchEgressPolicy(
            allow_private_network_targets=self._settings.web_fetch_allow_private_networks,
            allowed_schemes=web_fetch_allowed_scheme_set(
                self._settings.web_fetch_allowed_schemes
            ),
        )
        return anthropic_sse_streaming_response(
            stream_web_server_tool_response(
                routed.request,
                input_tokens=input_tokens,
                web_fetch_egress=egress,
                verbose_client_errors=self._settings.log_api_error_tracebacks,
            ),
        )

    def _intercept_local_optimization(
        self, routed: RoutedMessagesRequest
    ) -> object | None:
        optimized = try_optimizations(routed.request, self._settings)
        if optimized is None:
            return None
        trace_event(
            stage="routing",
            event="api.optimization.short_circuit",
            source="api",
            model=routed.request.model,
        )
        return optimized
