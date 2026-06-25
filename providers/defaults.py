"""Re-exports default upstream base URLs from the config provider catalog."""

from config.provider_catalog import (
    OPENCODE_DEFAULT_BASE,
    OPENCODE_GO_DEFAULT_BASE,
)

__all__ = (
    "OPENCODE_DEFAULT_BASE",
    "OPENCODE_GO_DEFAULT_BASE",
)
