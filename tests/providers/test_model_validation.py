"""Model validation tests: opencode-only."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from config.settings import Settings
from providers.base import BaseProvider, ProviderConfig
from providers.exceptions import ModelListResponseError, ServiceUnavailableError
from providers.model_listing import ProviderModelInfo
from providers.nvidia_nim import NvidiaNimProvider
from providers.ollama import OllamaProvider
from providers.open_router import OpenRouterProvider
from providers.runtime import ProviderRuntime
from providers.wafer import WaferProvider



def _settings(
    *,
    model: str = "opencode/deepseek-v4-flash-free",
    model_opus: str | None = None,
    model_sonnet: str | None = None,
    model_haiku: str | None = None,
    opencode_api_key: str = "test-key",
) -> Settings:
    return Settings.model_construct(
        model=model,
        model_opus=model_opus,
        model_sonnet=model_sonnet,
        model_haiku=model_haiku,
        opencode_api_key=opencode_api_key,
        log_api_error_tracebacks=False,
    )


class FakeProvider(BaseProvider):
    def __init__(
        self,
        model_ids: frozenset[str] | None = None,
        *,
        model_infos: frozenset[ProviderModelInfo] | None = None,
        error: BaseException | None = None,
        started: asyncio.Event | None = None,
        peer_started: asyncio.Event | None = None,
    ):
        super().__init__(ProviderConfig(api_key="test"))
        self._model_ids = model_ids or frozenset()
        self._model_infos = model_infos
        self._error = error
        self._started = started
        self._peer_started = peer_started
        self.cleaned = False

    async def cleanup(self) -> None:
        self.cleaned = True

    async def _before_model_list(self) -> None:
        if self._started is not None:
            self._started.set()
        if self._peer_started is not None:
            await self._peer_started.wait()
        if self._error is not None:
            raise self._error

    async def list_model_ids(self) -> frozenset[str]:
        await self._before_model_list()
        if self._model_infos is not None:
            return frozenset(info.model_id for info in self._model_infos)
        return self._model_ids

    async def list_model_infos(self) -> frozenset[ProviderModelInfo]:
        await self._before_model_list()
        if self._model_infos is not None:
            return self._model_infos
        return frozenset(ProviderModelInfo(model_id) for model_id in self._model_ids)

    async def send_request(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> str:
        raise NotImplementedError

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        if False:
            yield ""


@pytest.mark.asyncio
async def test_runtime_validation_succeeds_for_all_configured_models() -> None:
    settings = _settings(model_opus="open_router/anthropic/claude-opus")
    runtime = ProviderRuntime(
        settings,
        {
            "nvidia_nim": FakeProvider(frozenset({"nim-model"})),
            "open_router": FakeProvider(frozenset({"anthropic/claude-opus"})),
        },
    )


    await runtime.validate_configured_models()

    assert runtime.cached_model_ids() == {
        "nvidia_nim": frozenset({"nim-model"}),
        "open_router": frozenset({"anthropic/claude-opus"}),

    }


@pytest.mark.asyncio
async def test_runtime_validation_reports_missing_model_with_sources() -> None:
    settings = _settings(model_sonnet="nvidia_nim/nim-model")
    runtime = ProviderRuntime(
        settings,
        {"nvidia_nim": FakeProvider(frozenset({"different-model"}))},
    )


    with pytest.raises(ServiceUnavailableError) as exc_info:
        await runtime.validate_configured_models()

    message = exc_info.value.message
    assert "sources=MODEL_SONNET" in message
    assert "provider=opencode" in message
    assert "model=requested-model" in message
    assert "problem=missing model" in message


@pytest.mark.asyncio
async def test_runtime_validation_aggregates_multiple_failures() -> None:
    settings = _settings(model_opus="open_router/anthropic/claude-opus")
    runtime = ProviderRuntime(
        settings,
        {
            "opencode": FakeProvider(frozenset({"different-model"})),
            "opencode_go": FakeProvider(
                error=ModelListResponseError("bad model-list shape")
            ),
        },
    )


    with pytest.raises(ServiceUnavailableError) as exc_info:
        await runtime.validate_configured_models()

    message = exc_info.value.message
    assert "problem=missing model" in message


@pytest.mark.asyncio
async def test_runtime_validation_queries_providers_concurrently() -> None:
    nim_started = asyncio.Event()
    router_started = asyncio.Event()
    settings = _settings(model_opus="open_router/anthropic/claude-opus")
    runtime = ProviderRuntime(
        settings,

        {
            "opencode": FakeProvider(
                frozenset({"deepseek-v4-flash-free"}),
                started=opencode_started,
                peer_started=opencode_go_started,
            ),
            "opencode_go": FakeProvider(
                frozenset({"deepseek-v4-flash-go"}),
                started=opencode_go_started,
                peer_started=opencode_started,
            ),
        },
    )


    await asyncio.wait_for(runtime.validate_configured_models(), timeout=1.0)


@pytest.mark.asyncio
async def test_runtime_refresh_model_list_cache_uses_configured_remote_keys_and_referenced_local() -> (
    None
):
    settings = _settings(
        model="lmstudio/local-qwen",
        open_router_api_key="open-router-key",
    )
    runtime = ProviderRuntime(
        settings,
        {
            "open_router": FakeProvider(frozenset({"anthropic/claude-sonnet"})),
            "lmstudio": FakeProvider(frozenset({"local-qwen"})),
            "ollama": FakeProvider(frozenset({"llama3.1"})),
        },
    )


    await runtime.refresh_model_list_cache()

    assert runtime.cached_model_ids() == {
        "open_router": frozenset({"anthropic/claude-sonnet"}),
        "lmstudio": frozenset({"local-qwen"}),

    }


@pytest.mark.asyncio
async def test_runtime_refresh_model_list_cache_keeps_prior_cache_on_failure() -> None:
    settings = _settings(
        model="nvidia_nim/cached-model",
        nvidia_nim_api_key="nim-key",
    )
    runtime = ProviderRuntime(
        settings,
        {"nvidia_nim": FakeProvider(error=RuntimeError("upstream down"))},
    )
    runtime.cache_model_ids("nvidia_nim", {"cached-model"})


    await runtime.refresh_model_list_cache()

    assert runtime.cached_model_ids() == {"nvidia_nim": frozenset({"cached-model"})}


def test_runtime_metadata_cache_exposes_ids_and_prefixed_infos() -> None:
    runtime = ProviderRuntime(_settings())
    runtime.cache_model_infos(
        "open_router",

        {
            ProviderModelInfo("reasoning-model", supports_thinking=True),
            ProviderModelInfo("plain-model", supports_thinking=False),
        },
    )

    assert runtime.cached_model_ids() == {
        "open_router": frozenset({"reasoning-model", "plain-model"})
    }
    assert (
        runtime.cached_model_supports_thinking("open_router", "reasoning-model") is True
    )
    assert runtime.cached_model_supports_thinking("open_router", "plain-model") is False
    assert runtime.cached_prefixed_model_infos() == (
        ProviderModelInfo("open_router/plain-model", supports_thinking=False),
        ProviderModelInfo("open_router/reasoning-model", supports_thinking=True),
    )


def test_runtime_model_id_cache_keeps_unknown_thinking_support() -> None:
    runtime = ProviderRuntime(_settings())
    runtime.cache_model_ids("open_router", {"plain-model"})

    assert runtime.cached_model_ids() == {"open_router": frozenset({"plain-model"})}
    assert runtime.cached_model_supports_thinking("open_router", "plain-model") is None
    assert runtime.cached_prefixed_model_infos() == (
        ProviderModelInfo("open_router/plain-model", supports_thinking=None),
    )


def test_runtime_cached_prefixed_model_refs_are_deterministic() -> None:
    runtime = ProviderRuntime(_settings())
    runtime.cache_model_ids("deepseek", {"deepseek-chat"})
    runtime.cache_model_ids("open_router", {"z-model", "a-model"})

    assert runtime.cached_prefixed_model_refs() == (
        "open_router/a-model",
        "open_router/z-model",
        "deepseek/deepseek-chat",

    )
