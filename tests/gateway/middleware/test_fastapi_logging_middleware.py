"""
Regression tests for FastApiLoggingMiddleware.

Guards against re-introducing full-buffering of StreamingResponse bodies:
draining the whole body_iterator to log it would force the client to wait
for the entire upstream generation to finish before receiving any bytes,
defeating streaming outright (the exact "StreamingResponse not streaming"
failure mode).
"""

from __future__ import annotations

from typing import AsyncIterator, cast
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from language_model_gateway.gateway.middleware.fastapi_logging_middleware import (
    FastApiLoggingMiddleware,
    logger as mw_logger,
)


def _make_request(path: str = "/v1/messages") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("test", 1234),
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_dispatch_only_pulls_first_chunk_from_streaming_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dispatch() must not eagerly drain a StreamingResponse's body_iterator —
    only the first chunk is ever used for logging."""
    monkeypatch.setattr(mw_logger, "isEnabledFor", lambda level: True)

    pulled: list[int] = []

    async def gen() -> AsyncIterator[bytes]:
        pulled.append(1)
        yield b"chunk-1"
        pulled.append(2)
        yield b"chunk-2"
        pulled.append(3)
        yield b"chunk-3"

    response = StreamingResponse(gen(), media_type="text/event-stream")

    async def call_next(request: Request) -> Response:
        return response

    middleware = FastApiLoggingMiddleware(AsyncMock())
    result = cast(
        StreamingResponse, await middleware.dispatch(_make_request(), call_next)
    )

    # Only the first chunk should have been pulled during dispatch() itself —
    # this is the assertion that would fail if body_iterator were fully
    # drained (list comprehension) instead of peeked (single __anext__).
    assert pulled == [1]

    # The rest of the stream must still be lazily available afterwards, not
    # lost or replayed all at once.
    remaining = [chunk async for chunk in result.body_iterator]
    assert remaining == [b"chunk-1", b"chunk-2", b"chunk-3"]
    assert pulled == [1, 2, 3]


@pytest.mark.asyncio
async def test_dispatch_handles_empty_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mw_logger, "isEnabledFor", lambda level: True)

    async def gen() -> AsyncIterator[bytes]:
        return
        yield  # pragma: no cover - unreachable, makes this an async generator

    response = StreamingResponse(gen(), media_type="text/event-stream")

    async def call_next(request: Request) -> Response:
        return response

    middleware = FastApiLoggingMiddleware(AsyncMock())
    result = cast(
        StreamingResponse, await middleware.dispatch(_make_request(), call_next)
    )

    remaining = [chunk async for chunk in result.body_iterator]
    assert remaining == []


@pytest.mark.asyncio
async def test_dispatch_skips_health_check() -> None:
    call_next = AsyncMock(return_value=Response("ok"))
    middleware = FastApiLoggingMiddleware(AsyncMock())

    result = await middleware.dispatch(_make_request(path="/health"), call_next)

    assert result.body == b"ok"
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_non_streaming_response_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-streaming responses don't have a body_iterator and should pass through."""
    monkeypatch.setattr(mw_logger, "isEnabledFor", lambda level: True)

    response = Response(content=b"plain body", media_type="text/plain")

    async def call_next(request: Request) -> Response:
        return response

    middleware = FastApiLoggingMiddleware(AsyncMock())
    result = await middleware.dispatch(_make_request(), call_next)

    assert result.body == b"plain body"
