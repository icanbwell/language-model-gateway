import logging

import httpx

from language_model_gateway.gateway.utilities.logger.logging_response import (
    LoggingResponse,
)

logger = logging.getLogger(__name__)


class LoggingTransport(httpx.AsyncBaseTransport):
    """
    A custom HTTP transport that logs request and response details.
    This class extends httpx.AsyncBaseTransport to log the request method, URL,
    headers, and content before sending the request, and logs the response status code,
    headers, and content as it is streamed back.
    It is designed to be used with httpx for asynchronous HTTP requests.
    It logs the request method, URL, headers, and content before sending the request,
    and logs the response status code, headers, and content as it is streamed back.
    This transport can be used to monitor and debug HTTP requests and responses in an application.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        """
        Initialize the LoggingTransport with a given transport.
        Args:
            transport (httpx.AsyncBaseTransport): The underlying transport to wrap.
            This transport will handle the actual HTTP requests and responses.
        """
        self.transport: httpx.AsyncBaseTransport = transport

    async def handle_async_request(self, request: httpx.Request) -> LoggingResponse:
        """
        Handle an asynchronous HTTP request, logging the request details and returning a LoggingResponse.
        Args:
            request (httpx.Request): The HTTP request to handle.
        Returns:
            LoggingResponse: A custom response object that logs the response details.
        """
        # log the request
        logger.debug(f" ====== Request: {request.method} {request.url} =====")
        logger.debug(f"Headers: {request.headers}")
        # Log the actual Authorization header value if present
        if "authorization" in request.headers:
            logger.debug(f"Authorization header: {request.headers['authorization']}")
        if request.content:
            logger.debug(f"Content: {request.content.decode('utf-8', errors='ignore')}")

        response = await self.transport.handle_async_request(request)

        return LoggingResponse(
            status_code=response.status_code,
            headers=response.headers,
            stream=response.stream,
            extensions=response.extensions,
        )
