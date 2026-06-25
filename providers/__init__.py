"""Providers package - implement your own provider by extending BaseProvider.

Concrete adapters live in subpackages (``providers.opencode`` etc.) and are
registered via :data:`config.provider_catalog.PROVIDER_CATALOG`.
"""

from .base import BaseProvider, ProviderConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    InvalidRequestError,
    ModelListResponseError,
    OverloadedError,
    ProviderError,
    RateLimitError,
    UnknownProviderTypeError,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "BaseProvider",
    "InvalidRequestError",
    "ModelListResponseError",
    "OverloadedError",
    "ProviderConfig",
    "ProviderError",
    "RateLimitError",
    "UnknownProviderTypeError",
]
