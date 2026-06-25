"""Freeze ``PROVIDER_CATALOG`` insertion order used as canonical provider ranking."""

from __future__ import annotations

from config.provider_catalog import PROVIDER_CATALOG, SUPPORTED_PROVIDER_IDS

_EXPECTED_PROVIDER_ORDER: tuple[str, ...] = (
    "opencode",
    "opencode_go",
)


def test_provider_catalog_key_order_matches_canonical_plan() -> None:
    assert tuple(PROVIDER_CATALOG.keys()) == _EXPECTED_PROVIDER_ORDER
    assert SUPPORTED_PROVIDER_IDS == _EXPECTED_PROVIDER_ORDER
