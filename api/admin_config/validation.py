"""Settings-backed Admin UI config validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from config.settings import Settings

from .manifest import FIELDS, field_input_key


def validate_values(values: Mapping[str, str]) -> tuple[bool, list[str]]:
    """Validate proposed env values against the Settings model."""

    kwargs: dict[str, Any] = {"_env_file": None}
    for field in FIELDS:
        input_key = field_input_key(field)
        if input_key is None:
            continue
        kwargs[input_key] = values.get(field.key, "")

    try:
        Settings(**kwargs)
    except ValidationError as exc:
        return False, format_validation_errors(exc)
    return True, []


def _loc_to_env_key(loc: str) -> str | None:
    """Map a Pydantic validation loc (settings_attr or alias) to an env key."""
    for field in FIELDS:
        if field.settings_attr is None:
            continue
        input_key = field_input_key(field)
        if input_key == loc or field.settings_attr == loc:
            return field.key
    return None


def format_validation_errors(exc: ValidationError) -> list[str]:
    """Return user-readable validation errors from a Pydantic exception."""

    errors: list[str] = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value"))
        env_key = _loc_to_env_key(loc)
        if env_key:
            errors.append(f"{env_key}: {message}")
        else:
            errors.append(f"{loc}: {message}" if loc else message)
    return errors
