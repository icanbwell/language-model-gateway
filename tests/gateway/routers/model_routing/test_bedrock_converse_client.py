"""
Tests for bedrock_converse_client.py's boto3 client cache and error
classification helpers.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _converse_response_to_anthropic,
    _converse_stream_with_usage_tracking,
    _get_bedrock_runtime_client,
    _is_transient_bedrock_error_code,
    _iter_converse_stream_events,
    _openai_to_converse_request,
    _stream_bedrock_converse_to_anthropic,
)


class TestGetBedrockRuntimeClient:
    def test_creates_client_with_route_region(self) -> None:
        route = {"aws_region": "us-west-2"}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_client = MagicMock()
            mock_session_cls.return_value.client.return_value = mock_client

            result = _get_bedrock_runtime_client(route)

            assert result is mock_client
            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-west-2"
            )

    def test_defaults_region_to_us_east_1(self) -> None:
        route: dict[str, str] = {}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_session_cls.return_value.client.return_value = MagicMock()

            _get_bedrock_runtime_client(route)

            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-east-1"
            )

    def test_reuses_cached_client_for_same_region(self) -> None:
        route = {"aws_region": "us-east-1"}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_session_cls.return_value.client.return_value = MagicMock()

            first = _get_bedrock_runtime_client(route)
            second = _get_bedrock_runtime_client(route)

            assert first is second
            mock_session_cls.return_value.client.assert_called_once()

    def test_concurrent_calls_for_same_new_key_construct_only_one_client(
        self,
    ) -> None:
        route = {"aws_region": "us-east-1"}
        barrier = threading.Barrier(2)
        results: list[Any] = []

        def _call() -> None:
            barrier.wait()
            results.append(_get_bedrock_runtime_client(route))

        def _slow_client(*args: Any, **kwargs: Any) -> Any:
            time.sleep(0.001)
            return MagicMock()

        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
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


class TestOpenaiToConverseRequest:
    def test_plain_text_conversation(self) -> None:
        oai_body = {
            "model": "qwen.qwen3-coder-next",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024,
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["modelId"] == "qwen.qwen3-coder-next"
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hello"}]}]
        assert result["inferenceConfig"] == {"maxTokens": 1024}
        assert "system" not in result
        assert "toolConfig" not in result

    def test_system_prompt_becomes_system_field(self) -> None:
        oai_body = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["system"] == [{"text": "You are a helpful assistant."}]
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hi"}]}]

    def test_assistant_tool_call_becomes_tool_use_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Boston"}',
                            },
                        }
                    ],
                },
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assistant_msg = result["messages"][1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == [
            {
                "toolUse": {
                    "toolUseId": "call_1",
                    "name": "get_weather",
                    "input": {"city": "Boston"},
                }
            }
        ]

    def test_tool_result_becomes_user_turn_tool_result_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "72F, sunny"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        tool_result_msg = result["messages"][2]
        assert tool_result_msg == {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "call_1",
                        "content": [{"text": "72F, sunny"}],
                    }
                }
            ],
        }

    def test_tools_and_tool_choice_become_tool_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        },
                    },
                }
            ],
            "tool_choice": "auto",
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["tools"] == [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        }
                    },
                }
            }
        ]
        assert result["toolConfig"]["toolChoice"] == {"auto": {}}

    def test_specific_tool_choice_maps_to_named_tool(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "get_weather", "parameters": {}},
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["toolChoice"] == {"tool": {"name": "get_weather"}}

    def test_multi_turn_conversation_preserves_order(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Second question"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert [m["role"] for m in result["messages"]] == ["user", "assistant", "user"]
        assert result["messages"][0]["content"] == [{"text": "First question"}]
        assert result["messages"][1]["content"] == [{"text": "First answer"}]
        assert result["messages"][2]["content"] == [{"text": "Second question"}]

    def test_image_url_content_block_is_dropped_not_crashed(self) -> None:
        oai_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,abc123"},
                        },
                    ],
                }
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["messages"][0]["content"] == [{"text": "What's in this image?"}]

    def test_temperature_and_top_p_map_to_inference_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["inferenceConfig"] == {"temperature": 0.7, "topP": 0.9}

    def test_tool_choice_none_omits_tool_config_entirely(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "get_weather", "parameters": {}},
                }
            ],
            "tool_choice": "none",
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert "toolConfig" not in result

    def test_tool_choice_none_without_tools_still_omits_tool_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tool_choice": "none",
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert "toolConfig" not in result


class TestConverseResponseToAnthropic:
    def test_plain_text_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Hello there"}],
                }
            },
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["id"] == "msg_abc"
        assert result["type"] == "message"
        assert result["role"] == "assistant"
        assert result["content"] == [{"type": "text", "text": "Hello there"}]
        assert result["model"] == "qwen.qwen3-coder-next"
        assert result["stop_reason"] == "end_turn"
        assert result["stop_sequence"] is None
        assert result["usage"] == {"input_tokens": 10, "output_tokens": 5}

    def test_tool_use_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {"city": "Boston"},
                            }
                        }
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 20, "outputTokens": 8, "totalTokens": 28},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["content"] == [
            {
                "type": "tool_use",
                "id": "tooluse_1",
                "name": "get_weather",
                "input": {"city": "Boston"},
            }
        ]
        assert result["stop_reason"] == "tool_use"

    def test_mixed_text_and_tool_use_content(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check that for you."},
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {},
                            }
                        },
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["content"] == [
            {"type": "text", "text": "Let me check that for you."},
            {"type": "tool_use", "id": "tooluse_1", "name": "get_weather", "input": {}},
        ]

    def test_max_tokens_stop_reason_maps_directly(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "max_tokens",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["stop_reason"] == "max_tokens"

    def test_unknown_stop_reason_defaults_to_end_turn(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "guardrail_intervened",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["stop_reason"] == "end_turn"

    def test_missing_usage_defaults_to_zero(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "hi"}]}},
            "stopReason": "end_turn",
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["usage"] == {"input_tokens": 0, "output_tokens": 0}


class FakeSyncEventStream:
    """Stands in for boto3's synchronous EventStream — a plain iterator."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._iter = iter(events)

    def __iter__(self) -> "FakeSyncEventStream":
        return self

    def __next__(self) -> dict[str, Any]:
        return next(self._iter)


class FakeSyncEventStreamThatRaises:
    def __init__(self, events: list[dict[str, Any]], exc: Exception) -> None:
        self._iter = iter(events)
        self._exc = exc

    def __iter__(self) -> "FakeSyncEventStreamThatRaises":
        return self

    def __next__(self) -> dict[str, Any]:
        try:
            return next(self._iter)
        except StopIteration:
            raise self._exc from None


class TestIterConverseStreamEvents:
    @pytest.mark.asyncio
    async def test_yields_events_in_order(self) -> None:
        events = [
            {"messageStart": {"role": "assistant"}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]
        sync_stream = FakeSyncEventStream(events)
        result = [e async for e in _iter_converse_stream_events(sync_stream)]
        assert result == events

    @pytest.mark.asyncio
    async def test_propagates_exception_mid_stream(self) -> None:
        events = [{"messageStart": {"role": "assistant"}}]
        sync_stream = FakeSyncEventStreamThatRaises(events, RuntimeError("boom"))
        collected = []
        with pytest.raises(RuntimeError, match="boom"):
            async for e in _iter_converse_stream_events(sync_stream):
                collected.append(e)
        assert collected == events


class TestStreamBedrockConverseToAnthropic:
    @staticmethod
    async def _fake_events(
        events: list[dict[str, Any]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        for e in events:
            yield e

    @pytest.mark.asyncio
    async def test_text_only_stream_emits_expected_sse_sequence(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Hello"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 3, "outputTokens": 2}}},
            ]
        )
        usage_sink: dict[str, int] = {}
        text_sink: dict[str, str] = {}
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                usage_sink=usage_sink,
                text_sink=text_sink,
            )
        ]
        joined = b"".join(chunks).decode()
        assert "event: message_start" in joined
        assert "event: content_block_start" in joined
        assert '"type": "text"' in joined
        assert "event: content_block_delta" in joined
        assert '"text": "Hello"' in joined
        assert "event: content_block_stop" in joined
        assert "event: message_delta" in joined
        assert "event: message_stop" in joined
        assert usage_sink == {"input_tokens": 3, "output_tokens": 2}
        assert text_sink == {"output_text": "Hello"}

    @pytest.mark.asyncio
    async def test_tool_use_stream_emits_tool_use_block(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {
                    "contentBlockStart": {
                        "contentBlockIndex": 0,
                        "start": {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                            }
                        },
                    }
                },
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"toolUse": {"input": '{"city": "Boston"}'}},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "tool_use"}},
                {"metadata": {"usage": {"inputTokens": 5, "outputTokens": 4}}},
            ]
        )
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events, "msg_abc", "qwen.qwen3-coder-next"
            )
        ]
        joined = b"".join(chunks).decode()
        assert '"type": "tool_use"' in joined
        assert '"id": "tooluse_1"' in joined
        assert '"name": "get_weather"' in joined
        assert "input_json_delta" in joined
        assert '"partial_json": "{\\"city\\": \\"Boston\\"}"' in joined
        assert '"stop_reason": "tool_use"' in joined

    @pytest.mark.asyncio
    async def test_mid_stream_error_invokes_on_stream_error(self) -> None:
        async def _raising_events() -> AsyncGenerator[dict[str, Any], None]:
            yield {"messageStart": {"role": "assistant"}}
            raise RuntimeError("bedrock stream failed")

        captured: list[str] = []
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                _raising_events(),
                "msg_abc",
                "qwen.qwen3-coder-next",
                on_stream_error=captured.append,
            )
        ]
        assert captured == ["bedrock stream failed"]
        joined = b"".join(chunks).decode()
        assert "message_stop" in joined


_TEST_START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestConverseStreamWithUsageTracking:
    @staticmethod
    async def _fake_events(
        events: list[dict[str, Any]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        for e in events:
            yield e

    @pytest.mark.asyncio
    async def test_records_usage_after_stream_completes(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Hi"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 7, "outputTokens": 3}}},
            ]
        )
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()
        auth_info = {"user_id": "user-1", "session_id": "sess-1"}

        chunks = [
            c
            async for c in _converse_stream_with_usage_tracking(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                usage_tracker,
                auth_info,
                _TEST_START_TIME,
                model_tier="sonnet",
                backend="aws_bedrock",
            )
        ]
        assert b"".join(chunks)  # something was yielded

        await asyncio.sleep(0)  # let the fire-and-forget task run
        usage_tracker.record_usage.assert_awaited_once()
        call_kwargs = usage_tracker.record_usage.call_args.kwargs
        assert call_kwargs["request_id"] == "msg_abc"
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["model"] == "qwen.qwen3-coder-next"
        assert call_kwargs["input_tokens"] == 7
        assert call_kwargs["output_tokens"] == 3
        assert call_kwargs["model_tier"] == "sonnet"
        assert call_kwargs["backend"] == "aws_bedrock"
        assert call_kwargs["streaming"] is True
        assert call_kwargs["response_text"] == "Hi"

    @pytest.mark.asyncio
    async def test_skips_recording_when_no_tokens_used(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"messageStop": {"stopReason": "end_turn"}},
            ]
        )
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()

        _ = [
            c
            async for c in _converse_stream_with_usage_tracking(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                usage_tracker,
                {},
                _TEST_START_TIME,
            )
        ]
        await asyncio.sleep(0)
        usage_tracker.record_usage.assert_not_awaited()
