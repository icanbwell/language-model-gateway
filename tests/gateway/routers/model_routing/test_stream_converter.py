"""
Tests for stream_converter.py's client-disconnect handling and SSE event counting.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import httpx

from language_model_gateway.gateway.routers.model_routing.stream_converter import (
    _oai_stream_with_usage_tracking,
    _parse_anthropic_sse_usage,
    _stream_oai_sdk_to_anthropic,
    _stream_passthrough,
    _stream_passthrough_with_usage_tracking,
)

_TEST_START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fake_chunk(
    content: str | None = None,
    finish_reason: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> object:
    usage = None
    if prompt_tokens is not None or completion_tokens is not None:
        usage = SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content, tool_calls=None),
                finish_reason=finish_reason,
            )
        ],
        usage=usage,
    )


class TestDisconnectDetection:
    async def test_stream_oai_sdk_to_anthropic_stops_pulling_after_disconnect(
        self,
    ) -> None:
        """Once the client disconnects, no further upstream chunks are pulled —
        otherwise we keep paying for tokens nobody will receive."""
        pulled: list[str] = []

        async def fake_stream() -> AsyncIterator[object]:
            pulled.append("chunk-1")
            yield _fake_chunk(content="chunk-1")
            pulled.append("chunk-2")
            yield _fake_chunk(content="chunk-2")
            # Never reached if disconnect detection works.
            pulled.append("chunk-3")
            yield _fake_chunk(content="chunk-3")

        request = MagicMock()
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        chunks = [
            chunk
            async for chunk in _stream_oai_sdk_to_anthropic(
                fake_stream(), "msg_1", "upstream-model", request=request
            )
        ]

        # chunk-1 was processed (produced SSE bytes); chunk-3 was never pulled.
        assert pulled == ["chunk-1", "chunk-2"]
        assert any(b"chunk-1" in c for c in chunks)
        assert not any(b"chunk-3" in c for c in chunks)

    async def test_stream_oai_sdk_to_anthropic_no_request_streams_fully(self) -> None:
        """Without a request (e.g. no disconnect tracking needed), all chunks flow."""
        pulled: list[str] = []

        async def fake_stream() -> AsyncIterator[object]:
            for text in ("a", "b", "c"):
                pulled.append(text)
                yield _fake_chunk(content=text)

        chunks = [
            chunk
            async for chunk in _stream_oai_sdk_to_anthropic(
                fake_stream(), "msg_1", "upstream-model", request=None
            )
        ]

        assert pulled == ["a", "b", "c"]
        assert any(b"a" in c for c in chunks)
        assert any(b"c" in c for c in chunks)

    async def test_stream_passthrough_stops_pulling_after_disconnect(self) -> None:
        async def fake_aiter_bytes() -> AsyncIterator[bytes]:
            yield b"part-1"
            yield b"part-2"
            yield b"part-3"  # never reached

        resp = MagicMock(spec=httpx.Response)
        resp.aiter_bytes = fake_aiter_bytes
        resp.aclose = AsyncMock()
        client = MagicMock(spec=httpx.AsyncClient)
        client.aclose = AsyncMock()

        request = MagicMock()
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        received = [
            chunk async for chunk in _stream_passthrough(resp, client, request=request)
        ]

        assert received == [b"part-1"]
        resp.aclose.assert_awaited_once()
        client.aclose.assert_awaited_once()


class TestSseEventCount:
    async def test_records_sse_event_count_matching_yielded_chunks(self) -> None:
        async def fake_stream() -> AsyncIterator[object]:
            yield _fake_chunk(content="hello", finish_reason="stop")
            yield _fake_chunk(prompt_tokens=10, completion_tokens=5)

        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()
        http_client = MagicMock(spec=httpx.AsyncClient)
        http_client.aclose = AsyncMock()

        chunks = [
            chunk
            async for chunk in _oai_stream_with_usage_tracking(
                fake_stream(),
                "msg_1",
                "upstream-model",
                http_client,
                usage_tracker,
                {"user_id": "user-1"},
                _TEST_START_TIME,
            )
        ]

        # Let the fire-and-forget usage-recording task run.
        await asyncio.sleep(0)

        usage_tracker.record_usage.assert_awaited_once()
        recorded_count = usage_tracker.record_usage.call_args.kwargs["sse_event_count"]
        assert recorded_count == len(chunks)
        assert recorded_count > 0


def _anthropic_sse_event(event_type: str, data: dict[str, object]) -> bytes:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()


_MESSAGE_START = _anthropic_sse_event(
    "message_start",
    {
        "type": "message_start",
        "message": {
            "id": "msg_1",
            "usage": {"input_tokens": 42, "output_tokens": 1},
        },
    },
)
_CONTENT_DELTA = _anthropic_sse_event(
    "content_block_delta",
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "hello"},
    },
)
_MESSAGE_DELTA = _anthropic_sse_event(
    "message_delta",
    {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn"},
        "usage": {"output_tokens": 17},
    },
)
_MESSAGE_STOP = _anthropic_sse_event("message_stop", {"type": "message_stop"})


class TestParseAnthropicSseUsage:
    def test_extracts_input_and_output_tokens(self) -> None:
        raw = _MESSAGE_START + _CONTENT_DELTA + _MESSAGE_DELTA + _MESSAGE_STOP

        input_tokens, output_tokens, text = _parse_anthropic_sse_usage(raw)

        # message_delta's usage.output_tokens (the final cumulative count)
        # wins over message_start's placeholder output_tokens=1.
        assert input_tokens == 42
        assert output_tokens == 17
        assert text == "hello"

    def test_no_events_returns_zeros_and_none_text(self) -> None:
        input_tokens, output_tokens, text = _parse_anthropic_sse_usage(b"")
        assert (input_tokens, output_tokens, text) == (0, 0, None)

    def test_ignores_malformed_data_lines(self) -> None:
        raw = b"data: not-json\n\n" + _MESSAGE_START + _MESSAGE_DELTA
        input_tokens, output_tokens, _ = _parse_anthropic_sse_usage(raw)
        assert input_tokens == 42
        assert output_tokens == 17

    def test_concatenates_multiple_text_deltas(self) -> None:
        raw = _MESSAGE_START + _CONTENT_DELTA + _CONTENT_DELTA + _MESSAGE_DELTA
        _, _, text = _parse_anthropic_sse_usage(raw)
        assert text == "hellohello"


class TestStreamPassthroughWithUsageTracking:
    async def test_relays_bytes_verbatim_and_records_usage(self) -> None:
        async def fake_aiter_bytes() -> AsyncIterator[bytes]:
            yield _MESSAGE_START
            yield _CONTENT_DELTA
            yield _MESSAGE_DELTA
            yield _MESSAGE_STOP

        resp = MagicMock(spec=httpx.Response)
        resp.aiter_bytes = fake_aiter_bytes
        resp.aclose = AsyncMock()
        client = MagicMock(spec=httpx.AsyncClient)
        client.aclose = AsyncMock()
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()

        received = [
            chunk
            async for chunk in _stream_passthrough_with_usage_tracking(
                resp,
                client,
                usage_tracker,
                "req-1",
                {"user_id": "user-1"},
                "claude-opus-4-8",
                _TEST_START_TIME,
            )
        ]

        assert b"".join(received) == (
            _MESSAGE_START + _CONTENT_DELTA + _MESSAGE_DELTA + _MESSAGE_STOP
        )

        await asyncio.sleep(0)  # let the fire-and-forget task run

        usage_tracker.record_usage.assert_awaited_once()
        call_kwargs = usage_tracker.record_usage.call_args.kwargs
        assert call_kwargs["request_id"] == "req-1"
        assert call_kwargs["model"] == "claude-opus-4-8"
        assert call_kwargs["input_tokens"] == 42
        assert call_kwargs["output_tokens"] == 17
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["streaming"] is True
        assert call_kwargs["response_text"] == "hello"
        assert call_kwargs["start_time"] == _TEST_START_TIME
        resp.aclose.assert_awaited_once()
        client.aclose.assert_awaited_once()

    async def test_skips_recording_when_no_usage_found(self) -> None:
        async def fake_aiter_bytes() -> AsyncIterator[bytes]:
            yield b"event: ping\ndata: {}\n\n"

        resp = MagicMock(spec=httpx.Response)
        resp.aiter_bytes = fake_aiter_bytes
        resp.aclose = AsyncMock()
        client = MagicMock(spec=httpx.AsyncClient)
        client.aclose = AsyncMock()
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()

        _ = [
            chunk
            async for chunk in _stream_passthrough_with_usage_tracking(
                resp,
                client,
                usage_tracker,
                "req-1",
                {"user_id": "user-1"},
                "claude-opus-4-8",
                _TEST_START_TIME,
            )
        ]

        await asyncio.sleep(0)
        usage_tracker.record_usage.assert_not_awaited()

    async def test_stops_pulling_after_disconnect(self) -> None:
        async def fake_aiter_bytes() -> AsyncIterator[bytes]:
            yield _MESSAGE_START
            yield _MESSAGE_DELTA

        resp = MagicMock(spec=httpx.Response)
        resp.aiter_bytes = fake_aiter_bytes
        resp.aclose = AsyncMock()
        client = MagicMock(spec=httpx.AsyncClient)
        client.aclose = AsyncMock()
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()

        request = MagicMock()
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        received = [
            chunk
            async for chunk in _stream_passthrough_with_usage_tracking(
                resp,
                client,
                usage_tracker,
                "req-1",
                {"user_id": "user-1"},
                "claude-opus-4-8",
                _TEST_START_TIME,
                request=request,
            )
        ]

        assert received == [_MESSAGE_START]
        resp.aclose.assert_awaited_once()
        client.aclose.assert_awaited_once()
