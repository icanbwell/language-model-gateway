"""
Tests for bedrock_converse_client.py's boto3 client provider and error
classification helpers.
"""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    BedrockRuntimeClientProvider,
    _is_transient_bedrock_error_code,
)


class TestBedrockRuntimeClientProvider:
    def test_creates_client_with_route_region(self) -> None:
        route = {"aws_region": "us-west-2"}
        provider = BedrockRuntimeClientProvider()
        with patch("boto3.Session") as mock_session_cls:
            mock_client = MagicMock()
            mock_session_cls.return_value.client.return_value = mock_client

            result = provider.get_client(route)

            assert result is mock_client
            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-west-2"
            )

    def test_defaults_region_to_us_east_1(self) -> None:
        route: dict[str, str] = {}
        provider = BedrockRuntimeClientProvider()
        with patch("boto3.Session") as mock_session_cls:
            mock_session_cls.return_value.client.return_value = MagicMock()

            provider.get_client(route)

            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-east-1"
            )

    def test_reuses_cached_client_for_same_region(self) -> None:
        route = {"aws_region": "us-east-1"}
        provider = BedrockRuntimeClientProvider()
        with patch("boto3.Session") as mock_session_cls:
            mock_session_cls.return_value.client.return_value = MagicMock()

            first = provider.get_client(route)
            second = provider.get_client(route)

            assert first is second
            mock_session_cls.return_value.client.assert_called_once()

    def test_concurrent_calls_for_same_new_key_construct_only_one_client(
        self,
    ) -> None:
        route = {"aws_region": "us-east-1"}
        provider = BedrockRuntimeClientProvider()
        barrier = threading.Barrier(2)
        results: list[Any] = []

        def _call() -> None:
            barrier.wait()
            results.append(provider.get_client(route))

        def _slow_client(*args: Any, **kwargs: Any) -> Any:
            time.sleep(0.001)
            return MagicMock()

        with patch("boto3.Session") as mock_session_cls:
            mock_session_cls.return_value.client.side_effect = _slow_client
            threads = [threading.Thread(target=_call) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(results) == 2
        assert results[0] is results[1]
        assert mock_session_cls.return_value.client.call_count == 1


class TestIsTransientBedrockErrorCode:
    def test_throttling_exception_is_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ThrottlingException") is True

    def test_model_stream_error_exception_is_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ModelStreamErrorException") is True

    def test_validation_exception_is_not_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ValidationException") is False

    def test_none_is_not_transient(self) -> None:
        assert _is_transient_bedrock_error_code(None) is False
