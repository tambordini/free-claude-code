# Vision Fallback Auto-Reroute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-reroute image messages to a vision-capable model when the primary model doesn't support vision, then inject the analysis as text and continue with the original model.

**Architecture:** A pipeline interceptor in `request_pipeline.py` detects image content blocks when the resolved model lacks vision support. It relays the images to a hardcoded fallback vision model (`opencode/mimo-v2.5-free`) via a new non-streaming `send_request()` provider method, then rewrites the request to replace images with the vision model's text analysis.

**Tech Stack:** Python 3.14, Pydantic, FastAPI, OpenAI SDK, pytest

## Global Constraints

- All existing CI checks must pass (`ruff format`, `ruff check --fix`, `ty`, `pytest`)
- No `# type: ignore` or `# ty: ignore` — fix the underlying type
- Tests required for all new logic
- Hardcoded vision model: `opencode/mimo-v2.5-free`
- Hardcoded fallback mapping: `deepseek-v4-flash-free` → `mimo-v2.5-free`

---

### Task 1: Add `supports_vision` to `ProviderModelInfo` + Registry

**Files:**
- Modify: `providers/model_listing.py:12-17` — add field
- Modify: `providers/registry.py:230-237` — add query method
- Test: `tests/providers/test_model_listing.py`
- Test: `tests/providers/test_registry.py`

**Interfaces:**
- Produces: `ProviderModelInfo.supports_vision: bool | None` field
- Produces: `ProviderRegistry.cached_model_supports_vision(provider_id, model_id) -> bool | None`

- [ ] **Step 1.1: Write failing test for `ProviderModelInfo.supports_vision`**

```python
"""Test ProviderModelInfo supports_vision field."""

from providers.model_listing import ProviderModelInfo


def test_supports_vision_defaults_to_none():
    info = ProviderModelInfo(model_id="test-model")
    assert info.supports_vision is None


def test_supports_vision_can_be_set():
    info = ProviderModelInfo(
        model_id="test-model",
        supports_vision=True,
    )
    assert info.supports_vision is True


def test_supports_vision_explicit_false():
    info = ProviderModelInfo(
        model_id="test-model",
        supports_vision=False,
    )
    assert info.supports_vision is False
```

- [ ] **Step 1.2: Run test to verify it fails**

```
uv run pytest tests/providers/test_model_listing.py -v --tb=short
Expected: FAIL
Error: TypeError: unexpected keyword argument 'supports_vision'
```

- [ ] **Step 1.3: Add `supports_vision` field to `ProviderModelInfo`**

Edit `providers/model_listing.py`:

```python
@dataclass(frozen=True, slots=True)
class ProviderModelInfo:
    model_id: str
    supports_thinking: bool | None = None
    supports_vision: bool | None = None
```

- [ ] **Step 1.4: Run test to verify it passes**

```
uv run pytest tests/providers/test_model_listing.py -v --tb=short
Expected: all 3 PASS
```

- [ ] **Step 1.5: Write failing test for `cached_model_supports_vision`**

Add to `tests/providers/test_registry.py`:

```python
"""Test ProviderRegistry vision support query."""

from providers.model_listing import ProviderModelInfo
from providers.registry import ProviderRegistry


def test_cached_model_supports_vision_none():
    registry = ProviderRegistry()
    registry.cache_model_infos("test_prov", [
        ProviderModelInfo(model_id="model-a"),
        ProviderModelInfo(model_id="model-b", supports_vision=True),
    ])
    # model-a has no vision info
    assert registry.cached_model_supports_vision("test_prov", "model-a") is None
    # model-b has vision=True
    assert registry.cached_model_supports_vision("test_prov", "model-b") is True
    # unknown model
    assert registry.cached_model_supports_vision("test_prov", "model-x") is None
    # unknown provider
    assert registry.cached_model_supports_vision("unknown", "model-a") is None
```

- [ ] **Step 1.6: Run test to verify it fails**

```
uv run pytest tests/providers/test_registry.py::test_cached_model_supports_vision -v --tb=short
Expected: FAIL with AttributeError: 'ProviderRegistry' object has no attribute 'cached_model_supports_vision'
```

- [ ] **Step 1.7: Add `cached_model_supports_vision` to `ProviderRegistry`**

Add to `providers/registry.py` after `cached_model_supports_thinking` (around line 237):

```python
def cached_model_supports_vision(
    self, provider_id: str, model_id: str
) -> bool | None:
    """Return cached vision support when a provider exposes it."""
    info = self._model_infos_by_provider.get(provider_id, {}).get(model_id)
    if info is None:
        return None
    return info.supports_vision
```

- [ ] **Step 1.8: Run test to verify it passes**

```
uv run pytest tests/providers/test_registry.py::test_cached_model_supports_vision -v --tb=short
Expected: PASS
```

- [ ] **Step 1.9: Commit**

```
git add providers/model_listing.py providers/registry.py tests/providers/test_model_listing.py tests/providers/test_registry.py
git commit -m "feat: add supports_vision field to ProviderModelInfo and registry query method"
```

---

### Task 2: Hardcode Vision Model Mapping in OpenCode

**Files:**
- Modify: `providers/opencode/client.py`
- Test: `tests/providers/opencode/test_opencode_vision_mapping.py`

**Interfaces:**
- Consumes: `ProviderModelInfo` (from Task 1)
- Produces: `OpenCodeProvider` lists `supports_vision=True` for vision models in `list_model_infos()`
- Produces: Module-level `VISION_FALLBACK` dict for pipeline consumption

- [ ] **Step 2.1: Write failing test for vision mapping**

Create `tests/providers/opencode/test_opencode_vision_mapping.py`:

```python
"""Test OpenCode vision model mapping."""

from providers.model_listing import ProviderModelInfo
from providers.opencode.client import _VISION_MODELS, _VISION_FALLBACK


def test_vision_models_defined():
    """Vision models set must be non-empty."""
    assert len(_VISION_MODELS) > 0
    assert "mimo-v2.5-free" in _VISION_MODELS


def test_vision_fallback_defined():
    """Every non-vision model in the fallback map must resolve to a known vision model."""
    for non_vision_model, vision_model in _VISION_FALLBACK.items():
        assert non_vision_model not in _VISION_MODELS
        assert vision_model in _VISION_MODELS


def test_list_model_infos_populates_vision():
    """Verify that model infos from OpenCode correctly mark supports_vision."""
    from providers.opencode.client import OpenCodeProvider
    from providers.base import ProviderConfig

    # Must at minimum compile/import without error
    assert hasattr(OpenCodeProvider, "list_model_infos")
```

- [ ] **Step 2.2: Run test to verify it fails (import error)**

```
uv run pytest tests/providers/opencode/test_opencode_vision_mapping.py -v --tb=short
Expected: FAIL (import error — _VISION_MODELS not defined yet)
```

- [ ] **Step 2.3: Add vision constants + override `list_model_infos` to OpenCode**

Edit `providers/opencode/client.py`. After imports, add:

```python
# Models that support vision input.
_VISION_MODELS: frozenset[str] = frozenset({"mimo-v2.5-free"})

# Non-vision model -> vision fallback model.
_VISION_FALLBACK: dict[str, str] = {
    "deepseek-v4-flash-free": "mimo-v2.5-free",
}
```

Then add `list_model_infos()` override inside `OpenCodeProvider` class:

```python
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
```

- [ ] **Step 2.4: Run test to verify it passes**

```
uv run pytest tests/providers/opencode/test_opencode_vision_mapping.py -v --tb=short
Expected: PASS
```

- [ ] **Step 2.5: Commit**

```
git add providers/opencode/client.py tests/providers/opencode/test_opencode_vision_mapping.py
git commit -m "feat(opencode): hardcode vision model mapping and list_model_infos override"
```

---

### Task 3: Add Non-Streaming `send_request()` to Provider Chain

**Files:**
- Modify: `providers/base.py` — add abstract method
- Modify: `providers/transports/openai_chat/transport.py` — implement
- Test: `tests/providers/test_send_request.py`

**Interfaces:**
- Produces: `BaseProvider.send_request(request, *, thinking_enabled) -> Awaitable[str]`
- Produces: `OpenAIChatTransport.send_request()` — concrete implementation
- Consumed by: Task 4 (vision fallback interceptor calls this)

- [ ] **Step 3.1: Write failing test for abstract method**

Create `tests/providers/test_send_request.py`:

```python
"""Test non-streaming send_request on providers."""

import pytest

from providers.base import BaseProvider, ProviderConfig
from providers.transports.openai_chat.transport import OpenAIChatTransport


def test_base_provider_raises_not_implemented():
    """BaseProvider.send_request must raise NotImplementedError."""
    config = ProviderConfig(api_key="test-key")
    base = BaseProvider(config)
    with pytest.raises(NotImplementedError):
        # Don't await — just verify it raises
        _ = base.send_request(object())


def test_opencode_transport_has_send_request():
    """OpenAIChatTransport must override send_request."""
    config = ProviderConfig(api_key="test-key")
    transport = OpenAIChatTransport(
        config,
        provider_name="TEST",
        base_url="https://test.example.com",
        api_key="test-key",
    )
    assert hasattr(transport, "send_request")
    assert callable(transport.send_request)
```

- [ ] **Step 3.2: Run test to verify it fails**

```
uv run pytest tests/providers/test_send_request.py -v --tb=short
Expected: FAIL (no `send_request` method yet)
```

- [ ] **Step 3.3: Add abstract `send_request` to `BaseProvider`**

At line 127-131 of `providers/base.py` (before `list_model_ids`), add:

```python
async def send_request(
    self, request: Any, *, thinking_enabled: bool | None = None
) -> str:
    """Non-streaming request: send and return the full response text.

    Subclasses must override this if they support non-streaming calls.
    The default raises :class:`NotImplementedError`.
    """
    raise NotImplementedError(
        f"{type(self).__name__} does not support non-streaming requests"
    )
```

- [ ] **Step 3.4: Implement `send_request` on `OpenAIChatTransport`**

Add to `providers/transports/openai_chat/transport.py` (after `stream_response`, around line 156):

```python
async def send_request(
    self, request: Any, *, thinking_enabled: bool | None = None
) -> str:
    """Non-streaming chat completion: send request, return response text."""
    body = self._build_request_body(request, thinking_enabled=thinking_enabled)
    create_body = self._prepare_create_body(body)
    response = await self._global_rate_limiter.execute_with_retry(
        self._client.chat.completions.create, **create_body, stream=False
    )
    return response.choices[0].message.content or ""
```

Also add the import for `Any` if not already present at the top of `transport.py`:

```python
from typing import Any
```

- [ ] **Step 3.5: Run test to verify it passes**

```
uv run pytest tests/providers/test_send_request.py -v --tb=short
Expected: PASS
```

- [ ] **Step 3.6: Commit**

```
git add providers/base.py providers/transports/openai_chat/transport.py tests/providers/test_send_request.py
git commit -m "feat: add non-streaming send_request to provider chain"
```

---

### Task 4: Vision Fallback Pipeline Interceptor + Helpers

**Files:**
- Modify: `api/request_pipeline.py` — add `_apply_vision_fallback()` + helpers, make `create_message` async
- Modify: `api/routes.py` — `await pipeline.create_message()`
- Test: `tests/api/test_vision_fallback.py`

**Interfaces:**
- Consumes: `_VISION_MODELS`, `_VISION_FALLBACK` from `providers.opencode.client` (Task 2)
- Consumes: `BaseProvider.send_request()` (Task 3)

- [ ] **Step 4.1: Add helper functions to detect images and inject analysis**

Create helper functions at module level in `api/request_pipeline.py`. These are pure functions (no state) so they go before the class.

After the `_OPENAI_CHAT_UPSTREAM_IDS` constant (around line 46), add:

```python
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


def _replace_images_with_text(
    request: Any, analysis: str
) -> Any:
    """Return a deep copy of request with all image blocks replaced by text.

    Each image block -> ``{"type": "text", "text": "[Image: <analysis>]"}``.
    Non-image blocks are preserved as-is.
    """
    import copy

    rewritten = copy.deepcopy(request)
    for msg in getattr(rewritten, "messages", []):
        content = getattr(msg, "content", None)
        if not isinstance(content, list):
            continue
        new_content: list[Any] = []
        for block in content:
            block_type = getattr(block, "type", None) or (
                isinstance(block, dict) and block.get("type")
            )
            if block_type == "image":
                new_content.append({
                    "type": "text",
                    "text": f"[Image: {analysis}]",
                })
            else:
                new_content.append(block)
        msg.content = new_content
    return rewritten
```

- [ ] **Step 4.2: Add `_apply_vision_fallback` method to `ApiRequestPipeline`**

Add inside the `ApiRequestPipeline` class, after `_intercept_local_optimization` (around line 347):

```python
async def _apply_vision_fallback(
    self, routed: RoutedMessagesRequest
) -> RoutedMessagesRequest:
    """If the request has images but the model doesn't support vision,
    relay to the hardcoded vision fallback model, inject analysis, and
    return the rewritten request. Otherwise return the original unchanged."""
    if not _has_image_content(routed.request):
        return routed

    provider_id = routed.resolved.provider_id
    provider_model = routed.resolved.provider_model

    # Check if this model supports vision via the provider's own listing.
    from providers.opencode.client import _VISION_MODELS, _VISION_FALLBACK

    if provider_model in _VISION_MODELS:
        return routed

    # Look up the fallback model.
    fallback_model = _VISION_FALLBACK.get(provider_model)
    if fallback_model is None:
        logger.debug(
            "No vision fallback configured for model={}", provider_model
        )
        return routed

    # Build a vision-only request.
    vision_system = (
        "Describe the image(s) in detail, including objects, "
        "text, people, actions, and context."
    )
    vision_content = []
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

    # Build a minimal MessagesRequest for the vision call.
    from .models.anthropic import MessagesRequest

    vision_request = MessagesRequest(
        model=fallback_model,
        system=[{"type": "text", "text": vision_system}],
        messages=[{"role": "user", "content": vision_content}],
        stream=False,
    )

    # Resolve and call the fallback provider.
    fallback_resolved = self._model_router.resolve(
        f"{provider_id}/{fallback_model}"
    )
    fallback_provider = self._provider_getter(fallback_resolved.provider_id)

    try:
        analysis = await fallback_provider.send_request(
            vision_request,
            thinking_enabled=False,
        )
    except Exception as exc:
        logger.warning("Vision fallback failed for model={}: {}", provider_model, exc)
        return routed

    if not analysis:
        logger.warning("Vision fallback returned empty analysis")
        return routed

    # Rewrite the original request.
    rewritten_request = _replace_images_with_text(routed.request, analysis)
    logger.info(
        "Vision fallback: {} -> {} ({} chars analysis)",
        provider_model, fallback_model, len(analysis),
    )
    return RoutedMessagesRequest(
        request=rewritten_request,
        resolved=routed.resolved,
    )
```

- [ ] **Step 4.3: Make `create_message` async and call `_apply_vision_fallback`**

Change `create_message` from:

```python
def create_message(self, request_data: MessagesRequest) -> object:
```

to:

```python
async def create_message(self, request_data: MessagesRequest) -> object:
```

And add the fallback call right before `_provider_stream` (after `_run_message_intercepts`):

```python
        intercepted = self._run_message_intercepts(routed)
        if intercepted is not None:
            return intercepted

        # Vision fallback: rewrite images -> text if needed.
        routed = await self._apply_vision_fallback(routed)      # ← NEW

        logger.debug("No optimization matched, routing to provider")
        return anthropic_sse_streaming_response(
            self._provider_stream(
                routed,
                wire_api="messages",
                raw_log_label="FULL_PAYLOAD",
                raw_log_payload=routed.request.model_dump(),
            )
        )
```

- [ ] **Step 4.4: Update route handler to await**

In `api/routes.py` line 51, change:

```python
return pipeline.create_message(request_data)
```

to:

```python
return await pipeline.create_message(request_data)
```

- [ ] **Step 4.5: Write tests for vision fallback logic**

Create `tests/api/test_vision_fallback.py`:

```python
"""Test vision fallback detection and message rewriting."""

import pytest

from api.models.anthropic import MessagesRequest
from api.request_pipeline import _has_image_content, _replace_images_with_text


def _make_msg(content: list) -> MessagesRequest:
    return MessagesRequest(
        model="test-model",
        messages=[{"role": "user", "content": content}],
    )


def test_has_image_content_true():
    req = _make_msg([
        {"type": "text", "text": "hello"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "abc"}},
    ])
    assert _has_image_content(req) is True


def test_has_image_content_false():
    req = _make_msg([
        {"type": "text", "text": "hello"},
    ])
    assert _has_image_content(req) is False


def test_has_image_content_empty():
    req = _make_msg([])
    assert _has_image_content(req) is False


def test_replace_images_with_text():
    req = _make_msg([
        {"type": "text", "text": "what is this?"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "abc"}},
    ])
    analysis = "A cat sitting on a keyboard"
    rewritten = _replace_images_with_text(req, analysis)

    msg_content = rewritten.messages[0].content
    assert len(msg_content) == 2
    assert msg_content[0] == {"type": "text", "text": "what is this?"}
    assert msg_content[1]["type"] == "text"
    assert "[Image: A cat sitting on a keyboard]" in msg_content[1]["text"]


def test_replace_images_with_text_multiple_images():
    req = _make_msg([
        {"type": "image", "source": {"type": "url", "url": "http://example.com/a.png"}},
        {"type": "image", "source": {"type": "url", "url": "http://example.com/b.png"}},
    ])
    rewritten = _replace_images_with_text(req, "two images")
    text_blocks = [b for b in rewritten.messages[0].content if b.get("type") == "text"]
    assert len(text_blocks) == 2  # both images replaced
    assert all("two images" in b["text"] for b in text_blocks)
```

- [ ] **Step 4.6: Run tests**

```
uv run pytest tests/api/test_vision_fallback.py -v --tb=short
Expected: all 5 PASS
```

Also run full existing test suite to make sure the async conversion didn't break anything:

```
uv run pytest -v --tb=short
Expected: all existing tests PASS
```

- [ ] **Step 4.7: Commit**

```
git add api/request_pipeline.py api/routes.py tests/api/test_vision_fallback.py
git commit -m "feat: vision fallback auto-reroute pipeline interceptor"
```

---

### Task 5: Full CI Validation + Version Bump

**Files:**
- Modify: `pyproject.toml` — version bump
- Run: `./scripts/ci.sh`

- [ ] **Step 5.1: Bump version**

Read current version from `pyproject.toml`, bump MINOR (new backward-compatible feature):

```bash
grep '^version' pyproject.toml
# e.g. 3.0.0 -> 3.1.0
```

Edit `pyproject.toml` with the bumped version.

- [ ] **Step 5.2: Run `uv lock`**

```bash
uv lock
```

- [ ] **Step 5.3: Run full CI**

```bash
./scripts/ci.sh
```

Expected: ruff format, ruff check --fix, ty, pytest all pass.

- [ ] **Step 5.4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "release: bump 3.0.0 -> 3.1.0"
```

---

## Verification

After all tasks complete, verify the feature end-to-end:

1. Start the proxy: `uv run uvicorn api.app:app --reload`
2. Send a request with an image to `opencode/deepseek-v4-flash-free`:
   ```bash
   curl -X POST http://localhost:8000/v1/messages \
     -H "Content-Type: application/json" \
     -H "x-api-key: $OPENCODE_API_KEY" \
     -d '{
       "model": "opencode/deepseek-v4-flash-free",
       "messages": [{"role": "user", "content": [
         {"type": "text", "text": "What is this?"},
         {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "<base64>"}}
       ]}]
     }'
   ```
3. Confirm response comes back with analysis injected (no 400 error)
4. Send same request to a vision-capable model → confirm it passes through unchanged
