"""Vision fallback model mappings for providers that delegate vision to a different model."""

from __future__ import annotations

# Models that support vision input.
_VISION_MODELS: frozenset[str] = frozenset({"mimo-v2.5-free", "mimo-v2.5"})

# Non-vision model -> vision fallback model.
_VISION_FALLBACK: dict[str, str] = {
    "deepseek-v4-flash-free": "mimo-v2.5-free",
    "deepseek-v4-flash": "mimo-v2.5",
    "deepseek-v4-pro": "mimo-v2.5",
}
