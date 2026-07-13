"""
Tests for stream_converter.py's client-disconnect handling and SSE event counting.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import httpx

from language_model_gateway.gateway.routers.model_routing.stream_converter import (
    _oai_stream_with_usage_tracking,
    _stream_oai_sdk_to_anthropic,
    _stream_passthrough,
)


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
            )
        ]

        # Let the fire-and-forget usage-recording task run.
        await asyncio.sleep(0)

        usage_tracker.record_usage.assert_awaited_once()
        recorded_count = usage_tracker.record_usage.call_args.kwargs["sse_event_count"]
        assert recorded_count == len(chunks)
        assert recorded_count > 0
