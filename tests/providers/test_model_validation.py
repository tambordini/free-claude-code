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
from providers.registry import ProviderRegistry


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
async def test_registry_validation_succeeds_for_all_configured_models() -> None:
    registry = ProviderRegistry(
        {"opencode": FakeProvider(frozenset({"deepseek-v4-flash-free"}))}
    )
    settings = _settings(model="opencode/deepseek-v4-flash-free")

    await registry.validate_configured_models(settings)

    assert registry.cached_model_ids() == {
        "opencode": frozenset({"deepseek-v4-flash-free"}),
    }


@pytest.mark.asyncio
async def test_registry_validation_reports_missing_model_with_sources() -> None:
    registry = ProviderRegistry(
        {"opencode": FakeProvider(frozenset({"different-model"}))}
    )
    settings = _settings(model_sonnet="opencode/requested-model")

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await registry.validate_configured_models(settings)

    message = exc_info.value.message
    assert "sources=MODEL_SONNET" in message
    assert "provider=opencode" in message
    assert "model=requested-model" in message
    assert "problem=missing model" in message


@pytest.mark.asyncio
async def test_registry_validation_aggregates_multiple_failures() -> None:
    registry = ProviderRegistry(
        {
            "opencode": FakeProvider(frozenset({"different-model"})),
            "opencode_go": FakeProvider(
                error=ModelListResponseError("bad model-list shape")
            ),
        }
    )
    settings = _settings(
        model_opus="opencode/deepseek-v4-flash-free",
        model_haiku="opencode_go/other-model",
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await registry.validate_configured_models(settings)

    message = exc_info.value.message
    assert "problem=missing model" in message


@pytest.mark.asyncio
async def test_registry_validation_queries_providers_concurrently() -> None:
    opencode_started = asyncio.Event()
    opencode_go_started = asyncio.Event()
    registry = ProviderRegistry(
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
        }
    )
    settings = _settings(
        model_sonnet="opencode/deepseek-v4-flash-free",
        model_opus="opencode_go/deepseek-v4-flash-go",
    )

    await asyncio.wait_for(registry.validate_configured_models(settings), timeout=1.0)


@pytest.mark.asyncio
async def test_registry_refresh_model_list_cache_uses_configured_keys() -> None:
    registry = ProviderRegistry(
        {
            "opencode": FakeProvider(frozenset({"deepseek-v4-flash-free"})),
            "opencode_go": FakeProvider(frozenset({"go-model"})),
        }
    )
    settings = _settings(model="opencode/deepseek-v4-flash-free")

    await registry.refresh_model_list_cache(settings)

    assert registry.cached_model_ids() == {
        "opencode": frozenset({"deepseek-v4-flash-free"}),
        "opencode_go": frozenset({"go-model"}),
    }


@pytest.mark.asyncio
async def test_registry_refresh_model_list_cache_keeps_prior_cache_on_failure() -> None:
    registry = ProviderRegistry(
        {
            "opencode": FakeProvider(error=RuntimeError("upstream down")),
            "opencode_go": FakeProvider(frozenset({"go-model"})),
        }
    )
    registry.cache_model_ids("opencode", {"cached-model"})
    settings = _settings(model="opencode/cached-model")

    await registry.refresh_model_list_cache(settings)

    assert registry.cached_model_ids() == {
        "opencode": frozenset({"cached-model"}),
        "opencode_go": frozenset({"go-model"}),
    }


def test_registry_metadata_cache_exposes_ids_and_prefixed_infos() -> None:
    registry = ProviderRegistry()
    registry.cache_model_infos(
        "opencode",
        {
            ProviderModelInfo("reasoning-model", supports_thinking=True),
            ProviderModelInfo("plain-model", supports_thinking=False),
        },
    )

    assert registry.cached_model_ids() == {
        "opencode": frozenset({"reasoning-model", "plain-model"})
    }
    assert (
        registry.cached_model_supports_thinking("opencode", "reasoning-model") is True
    )
    assert registry.cached_model_supports_thinking("opencode", "plain-model") is False
    assert registry.cached_prefixed_model_infos() == (
        ProviderModelInfo("opencode/plain-model", supports_thinking=False),
        ProviderModelInfo("opencode/reasoning-model", supports_thinking=True),
    )


def test_registry_legacy_model_id_cache_keeps_unknown_thinking_support() -> None:
    registry = ProviderRegistry()
    registry.cache_model_ids("opencode", {"plain-model"})

    assert registry.cached_model_ids() == {"opencode": frozenset({"plain-model"})}
    assert registry.cached_model_supports_thinking("opencode", "plain-model") is None
    assert registry.cached_prefixed_model_infos() == (
        ProviderModelInfo("opencode/plain-model", supports_thinking=None),
    )


def test_registry_cached_prefixed_model_refs_are_deterministic() -> None:
    registry = ProviderRegistry()
    registry.cache_model_ids("opencode", {"b-model", "a-model"})

    assert registry.cached_prefixed_model_refs() == (
        "opencode/a-model",
        "opencode/b-model",
    )
