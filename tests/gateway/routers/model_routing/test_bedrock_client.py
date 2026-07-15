"""
Tests for bedrock_client.py's retry/transient-error classification logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from language_model_gateway.gateway.routers.model_routing.bedrock_client import (
    _is_transient_stream_error,
    _send_with_bedrock_retry,
)
from language_model_gateway.gateway.routers.model_routing.constants import (
    _MAX_THROTTLE_RETRIES,
)

_SIGN_BEDROCK = (
    "language_model_gateway.gateway.routers.model_routing.bedrock_client._sign_bedrock"
)
_THROTTLE_BACKOFF = (
    "language_model_gateway.gateway.routers.model_routing.bedrock_client."
    "_throttle_backoff"
)


class TestIsTransientStreamError:
    @pytest.mark.parametrize(
        "code,type_,text,expected",
        [
            ("ModelStreamErrorException", None, "", True),
            (None, "ThrottlingException", "", True),
            (None, None, "please try again later", True),
            ("ValidationException", "invalid_request_error", "bad input", False),
            (None, None, "", False),
        ],
    )
    def test_classification(
        self, code: str | None, type_: str | None, text: str, expected: bool
    ) -> None:
        assert _is_transient_stream_error(code, type_, text) is expected


class TestSendWithBedrockRetry:
    """A transport-level failure (timeout, connection reset, DNS) previously
    propagated on the first attempt with no retry at all — unlike an
    HTTP-level throttle response, which already got backoff+retry."""

    async def test_retries_transport_error_then_succeeds(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        client.build_request = MagicMock(return_value=MagicMock())
        success_resp = MagicMock(spec=httpx.Response)
        success_resp.status_code = 200
        client.send = AsyncMock(
            side_effect=[httpx.ConnectError("connection refused"), success_resp]
        )

        with (
            patch(_SIGN_BEDROCK, return_value={}),
            patch(_THROTTLE_BACKOFF, return_value=0),
        ):
            resp, retry_count = await _send_with_bedrock_retry(
                client,
                "https://example.bedrock.aws/v1/messages",
                {},
                b"{}",
                {},
                "aws",
            )

        assert resp is success_resp
        assert retry_count == 1
        assert client.send.await_count == 2

    async def test_gives_up_after_max_retries(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        client.build_request = MagicMock(return_value=MagicMock())
        client.send = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with (
            patch(_SIGN_BEDROCK, return_value={}),
            patch(_THROTTLE_BACKOFF, return_value=0),
        ):
            with pytest.raises(httpx.ConnectError):
                await _send_with_bedrock_retry(
                    client,
                    "https://example.bedrock.aws/v1/messages",
                    {},
                    b"{}",
                    {},
                    "aws",
                )

        # Initial attempt + _MAX_THROTTLE_RETRIES retries, all exhausted.
        assert client.send.await_count == _MAX_THROTTLE_RETRIES + 1

    async def test_non_aws_auth_does_not_retry_transport_error(self) -> None:
        """Only auth="aws" (Bedrock) gets this retry treatment — a direct
        Anthropic passthrough call isn't Bedrock's retry policy to apply."""
        client = MagicMock(spec=httpx.AsyncClient)
        client.build_request = MagicMock(return_value=MagicMock())
        client.send = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with pytest.raises(httpx.ConnectError):
            await _send_with_bedrock_retry(
                client,
                "https://api.anthropic.com/v1/messages",
                {},
                b"{}",
                {},
                "passthrough",
            )

        assert client.send.await_count == 1
