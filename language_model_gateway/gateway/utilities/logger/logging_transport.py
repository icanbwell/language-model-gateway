import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class LogResponse(httpx.Response):
    async def aiter_bytes(self, *args: Any, **kwargs: Any) -> AsyncIterator[bytes]:
        async for chunk in super().aiter_bytes(*args, **kwargs):
            logger.debug(chunk)
            yield chunk


class LoggingTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        self.transport = transport

    async def handle_async_request(self, request: httpx.Request) -> LogResponse:
        # log the request
        logger.debug(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {request.headers}")
        if request.content:
            logger.debug(f"Content: {request.content.decode('utf-8', errors='ignore')}")

        response = await self.transport.handle_async_request(request)

        return LogResponse(
            status_code=response.status_code,
            headers=response.headers,
            stream=response.stream,
            extensions=response.extensions,
        )
