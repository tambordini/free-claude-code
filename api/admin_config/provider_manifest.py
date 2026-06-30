"""Catalog-derived Admin UI provider fields."""

from __future__ import annotations

from typing import Any

from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings

_PROVIDER_FIELD_OVERRIDES: dict[str, dict[str, Any]] = {
    "OPENCODE_API_KEY": {
        "label": "OpenCode API Key",
        "description": (
            "OpenCode Zen curated gateway (opencode.ai/zen/v1) and OpenCode Go subscription "
            "gateway (opencode.ai/zen/go/v1); single key from opencode.ai/auth."
        ),
    },
}


def provider_field_specs() -> tuple[dict[str, Any], ...]:
    """Return provider fields generated from the provider catalog."""

    return (
        *_credential_field_specs(),
        *_local_base_url_field_specs(),
        *_proxy_field_specs(),
    )


def _credential_field_specs() -> tuple[dict[str, Any], ...]:
    specs: list[dict[str, Any]] = []
    seen_env_keys: set[str] = set()
    for descriptor in PROVIDER_CATALOG.values():
        if descriptor.credential_env is None:
            continue
        if descriptor.credential_env in seen_env_keys:
            continue
        seen_env_keys.add(descriptor.credential_env)
        spec = {
            "key": descriptor.credential_env,
            "label": f"{descriptor.display_name} API Key",
            "section_id": "providers",
            "field_type": "secret",
            "settings_attr": descriptor.credential_attr,
            "secret": True,
        }
        spec.update(_PROVIDER_FIELD_OVERRIDES.get(descriptor.credential_env, {}))
        specs.append(spec)
    return tuple(specs)


def _local_base_url_field_specs() -> tuple[dict[str, Any], ...]:
    specs: list[dict[str, Any]] = []
    for descriptor in PROVIDER_CATALOG.values():
        if descriptor.base_url_attr is None:
            continue
        specs.append(
            {
                "key": _settings_env_key(descriptor.base_url_attr),
                "label": f"{descriptor.display_name} Base URL",
                "section_id": "providers",
                "settings_attr": descriptor.base_url_attr,
                "default": descriptor.default_base_url or "",
            }
        )
    return tuple(specs)


def _proxy_field_specs() -> tuple[dict[str, Any], ...]:
    specs: list[dict[str, Any]] = []
    for descriptor in PROVIDER_CATALOG.values():
        if descriptor.proxy_attr is None:
            continue
        specs.append(
            {
                "key": _settings_env_key(descriptor.proxy_attr),
                "label": f"{descriptor.display_name} Proxy",
                "section_id": "providers",
                "field_type": "secret",
                "settings_attr": descriptor.proxy_attr,
                "secret": True,
                "advanced": True,
            }
        )
    return tuple(specs)


def _settings_env_key(settings_attr: str) -> str:
    model_field = Settings.model_fields[settings_attr]
    alias = model_field.validation_alias
    return str(alias) if alias is not None else settings_attr
