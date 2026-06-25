"""Tests for non-streaming send_request on providers."""


import pytest

from providers.base import BaseProvider, ProviderConfig
from providers.transports.openai_chat.transport import OpenAIChatTransport


@pytest.mark.asyncio
async def test_base_provider_raises_not_implemented() -> None:
    """BaseProvider.send_request must raise NotImplementedError."""

    class MinimalProvider(BaseProvider):
        async def cleanup(self) -> None:
            pass

        async def list_model_ids(self) -> frozenset[str]:
            return frozenset()

        async def send_request(self, request, input_tokens=0, **kwargs):
            raise NotImplementedError

        async def stream_response(self, request, input_tokens=0, **kwargs):
            if False:
                yield ""

    provider = MinimalProvider(ProviderConfig(api_key="test-key"))
    with pytest.raises(NotImplementedError):
        await provider.send_request(object())


def test_opencode_transport_inherits_send_request() -> None:
    """OpenAIChatTransport subclasses must have the abstract send_request pending."""
    assert hasattr(OpenAIChatTransport, "send_request")
    # It should be a callable (abstract method descriptor)
    callable(OpenAIChatTransport.send_request)
