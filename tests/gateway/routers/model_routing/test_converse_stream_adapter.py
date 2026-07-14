"""
Tests for converse_stream_adapter.py's Bedrock Converse event stream ->
Anthropic SSE adaptation and usage-tracking wrapper.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from language_model_gateway.gateway.routers.model_routing.converse_stream_adapter import (
    _converse_stream_with_usage_tracking,
    _iter_converse_stream_events,
    _stream_bedrock_converse_to_anthropic,
)


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
        usage_sink: dict[str, Any] = {}
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
        assert usage_sink == {
            "input_tokens": 3,
            "output_tokens": 2,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "raw_usage": {"inputTokens": 3, "outputTokens": 2},
        }
        assert text_sink == {"output_text": "Hello"}

    @pytest.mark.asyncio
    async def test_cache_tokens_are_mapped_into_usage_sink_and_message_delta(
        self,
    ) -> None:
        """Bedrock's cacheReadInputTokens/cacheWriteInputTokens must reach
        both the usage_sink (for usage-tracker recording) and the emitted
        message_delta SSE event (for the client's own context-usage
        accounting). See anthropics/claude-code#13385."""
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
                {
                    "metadata": {
                        "usage": {
                            "inputTokens": 50,
                            "outputTokens": 10,
                            "cacheReadInputTokens": 100,
                            "cacheWriteInputTokens": 20,
                        }
                    }
                },
            ]
        )
        usage_sink: dict[str, Any] = {}
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events, "msg_abc", "qwen.qwen3-coder-next", usage_sink=usage_sink
            )
        ]
        joined = b"".join(chunks).decode()
        assert usage_sink["cache_read_input_tokens"] == 100
        assert usage_sink["cache_creation_input_tokens"] == 20
        assert usage_sink["raw_usage"] == {
            "inputTokens": 50,
            "outputTokens": 10,
            "cacheReadInputTokens": 100,
            "cacheWriteInputTokens": 20,
        }
        assert '"cache_read_input_tokens": 100' in joined
        assert '"cache_creation_input_tokens": 20' in joined

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
    async def test_tool_use_stream_restores_original_long_name(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {
                    "contentBlockStart": {
                        "contentBlockIndex": 0,
                        "start": {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "safe_name_123",
                            }
                        },
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "tool_use"}},
            ]
        )
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                tool_name_map={
                    "safe_name_123": "mcp__claude_ai_Intuit_QuickBooks__original_name"
                },
            )
        ]
        joined = b"".join(chunks).decode()
        assert '"name": "mcp__claude_ai_Intuit_QuickBooks__original_name"' in joined

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

    @pytest.mark.asyncio
    async def test_early_mid_stream_error_injects_visible_error_text(self) -> None:
        """An error raised before any contentBlockStart (the common case for
        a fast-failing upstream) must produce visible error text in the SSE
        output, not a silently empty assistant message — message_start is
        emitted eagerly at the top of this function, so unlike Mantle's lazy
        message_start gate, this path needs its own "no block ever opened"
        check to know it's safe to inject inline error text."""

        async def _raising_events() -> AsyncGenerator[dict[str, Any], None]:
            yield {"messageStart": {"role": "assistant"}}
            raise RuntimeError("bedrock stream failed before first token")

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
        joined = b"".join(chunks).decode()
        assert "[bedrock-native-proxy error]" in joined
        assert "bedrock stream failed before first token" in joined
        assert "event: content_block_start" in joined
        assert "event: content_block_stop" in joined
        assert "event: message_stop" in joined

    @pytest.mark.asyncio
    async def test_delta_without_prior_start_is_lazily_opened(self) -> None:
        """Observed live with qwen.qwen3-coder-next over the native Bedrock
        transport: the upstream skips contentBlockStart entirely and goes
        straight to contentBlockDelta. Forwarding that delta without ever
        having sent a content_block_start breaks Claude Code's SSE parser
        ("Content block not found") and starves its context-usage tracking,
        which is what makes the context bar read 0% until auto-compact."""
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Hi! How can I help you today?"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 9, "outputTokens": 10}}},
            ]
        )
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events, "msg_abc", "qwen.qwen3-coder-next"
            )
        ]
        joined = b"".join(chunks).decode()
        start_idx = joined.index("event: content_block_start")
        delta_idx = joined.index("event: content_block_delta")
        assert start_idx < delta_idx
        assert '"type": "text"' in joined
        assert "Hi! How can I help you today?" in joined

    @pytest.mark.asyncio
    async def test_no_visible_content_still_opens_a_content_block(self) -> None:
        """A completion that ends with no content block ever opened and no
        error (e.g. the model exhausted its token budget entirely within
        hidden reasoning) must still produce a well-formed message — a
        message with content=[] isn't valid Anthropic protocol and breaks
        Claude Code's SSE parser."""
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"messageStop": {"stopReason": "max_tokens"}},
                {"metadata": {"usage": {"inputTokens": 9, "outputTokens": 32768}}},
            ]
        )
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events, "msg_abc", "qwen.qwen3-coder-next"
            )
        ]
        joined = b"".join(chunks).decode()
        assert "event: content_block_start" in joined
        assert "event: content_block_stop" in joined
        assert '"stop_reason": "max_tokens"' in joined


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
        assert call_kwargs["raw_usage"] == {"inputTokens": 7, "outputTokens": 3}

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
