"""Registry tests: opencode-only."""

import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.provider_catalog import PROVIDER_CATALOG
from config.provider_ids import SUPPORTED_PROVIDER_IDS
from providers.exceptions import UnknownProviderTypeError
from providers.opencode import OpenCodeProvider
from providers.registry import (
    PROVIDER_DESCRIPTORS,
    ProviderRegistry,
    build_provider_config,
    create_provider,
)


def _make_settings(**overrides):
    mock = MagicMock()
    mock.opencode_api_key = "test_opencode_key"
    mock.opencode_proxy = ""
    mock.opencode_go_proxy = ""
    mock.provider_rate_limit = 40
    mock.provider_rate_window = 60
    mock.provider_max_concurrency = 5
    mock.http_read_timeout = 300.0
    mock.http_write_timeout = 10.0
    mock.http_connect_timeout = 10.0
    mock.enable_model_thinking = True
    mock.log_raw_sse_events = False
    mock.log_api_error_tracebacks = False
    for key, value in overrides.items():
        setattr(mock, key, value)
    return mock


def test_importing_registry_does_not_eager_load_provider_adapters() -> None:
    """Registry metadata must not import every provider adapter up front."""
    code = (
        "import sys\n"
        "import providers.registry\n"
        "assert 'providers.opencode' not in sys.modules\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_descriptors_cover_advertised_provider_ids():
    assert set(PROVIDER_DESCRIPTORS) == set(SUPPORTED_PROVIDER_IDS)
    for descriptor in PROVIDER_DESCRIPTORS.values():
        assert descriptor.provider_id
        assert descriptor.transport_type in {"openai_chat", "anthropic_messages"}
        assert descriptor.capabilities


def test_opencode_go_provider_config_uses_correct_base_url_and_name():
    with patch("httpx.AsyncClient"):
        provider = create_provider("opencode_go", _make_settings())

    assert isinstance(provider, OpenCodeProvider)
    assert provider._base_url == "https://opencode.ai/zen/go/v1"
    assert provider._provider_name == "OPENCODE_GO"
    assert provider._api_key == "test_opencode_key"


def test_opencode_go_catalog_uses_opencode_api_key() -> None:
    desc = PROVIDER_CATALOG["opencode_go"]

    assert desc.credential_env == "OPENCODE_API_KEY"
    assert desc.credential_attr == "opencode_api_key"


def test_build_provider_config_opencode_go_uses_opencode_api_key() -> None:
    descriptor = PROVIDER_CATALOG["opencode_go"]
    settings = _make_settings(opencode_api_key="shared-opencode-token")

    config = build_provider_config(descriptor, settings)

    assert config.api_key == "shared-opencode-token"


def test_create_provider_instantiates_each_builtin():
    settings = _make_settings()
    cases = {
        "opencode": OpenCodeProvider,
        "opencode_go": OpenCodeProvider,
    }

    with patch("httpx.AsyncClient"):
        for provider_id, provider_cls in cases.items():
            assert isinstance(create_provider(provider_id, settings), provider_cls)


def test_provider_registry_caches_by_provider_id():
    registry = ProviderRegistry()
    settings = _make_settings()

    with patch("httpx.AsyncClient"):
        first = registry.get("opencode", settings)
        second = registry.get("opencode", settings)

    assert first is second


def test_unknown_provider_raises_unknown_provider_type_error():
    with pytest.raises(UnknownProviderTypeError, match="Unknown provider_type"):
        create_provider("unknown", _make_settings())


@pytest.mark.asyncio
async def test_provider_registry_cleanup_runs_all_even_if_one_fails() -> None:
    """Every provider gets cleanup; cache is cleared even when one raises."""
    reg = ProviderRegistry()
    p1 = MagicMock()
    p1.cleanup = AsyncMock(side_effect=RuntimeError("first"))
    p2 = MagicMock()
    p2.cleanup = AsyncMock()
    reg._providers["a"] = p1
    reg._providers["b"] = p2
    with pytest.raises(RuntimeError, match="first"):
        await reg.cleanup()
    p1.cleanup.assert_awaited_once()
    p2.cleanup.assert_awaited_once()
    assert reg._providers == {}


@pytest.mark.asyncio
async def test_provider_registry_cleanup_exceptiongroup_on_multiple_failures() -> None:
    reg = ProviderRegistry()
    p1 = MagicMock()
    p1.cleanup = AsyncMock(side_effect=RuntimeError("a"))
    p2 = MagicMock()
    p2.cleanup = AsyncMock(side_effect=RuntimeError("b"))
    reg._providers["x"] = p1
    reg._providers["y"] = p2
    with pytest.raises(ExceptionGroup) as exc_info:
        await reg.cleanup()
    assert len(exc_info.value.exceptions) == 2
    assert reg._providers == {}
