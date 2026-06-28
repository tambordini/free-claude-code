"""OpenCode Zen provider implementation (OpenAI-compatible Chat Completions)."""

from __future__ import annotations

from typing import Any

from providers.base import ProviderConfig
from providers.defaults import OPENCODE_DEFAULT_BASE
from providers.model_listing import ProviderModelInfo
from providers.transports.openai_chat import (
    OpenAIChatRequestPolicy,
    OpenAIChatTransport,
    build_openai_chat_request_body,
)

# Models that support vision input.
_VISION_MODELS: frozenset[str] = frozenset({"mimo-v2.5-free", "mimo-v2.5"})



# Non-vision model -> vision fallback model.
_VISION_FALLBACK: dict[str, str] = {
    "deepseek-v4-flash-free": "mimo-v2.5-free",
    "deepseek-v4-flash": "mimo-v2.5",
    "deepseek-v4-pro": "mimo-v2.5",



>>>>>>> 2da755a (feat: Update deepseek v4 pro fallback vision to mimo 2.5)
}



class OpenCodeProvider(OpenAIChatTransport):
    """OpenCode Zen provider using ``https://opencode.ai/zen/v1/chat/completions``."""

    def __init__(self, config: ProviderConfig, provider_name: str = "OPENCODE"):
        super().__init__(
            config,
            provider_name=provider_name,
            base_url=config.base_url or OPENCODE_DEFAULT_BASE,
            api_key=config.api_key,
        )
        self._request_policy = OpenAIChatRequestPolicy(provider_name=provider_name)

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_openai_chat_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
            policy=self._request_policy,
        )

    async def list_model_infos(self) -> frozenset[ProviderModelInfo]:
        """Return model info with vision capability metadata."""
        model_ids = await self.list_model_ids()
        return frozenset(
            ProviderModelInfo(
                model_id=mid,
                supports_vision=mid in _VISION_MODELS,
            )
            for mid in model_ids
            if mid.strip()
        )
