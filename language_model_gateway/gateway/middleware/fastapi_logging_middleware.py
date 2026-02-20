import logging
import os
import time
import uuid
from typing import override, Callable, Awaitable, cast, AsyncIterable, AsyncIterator

from oidcauthlib.utilities.environment.oidc_environment_variables import OidcEnvironmentVariables
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from starlette.types import ASGIApp

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["HTTP_TRACING"])



class FastApiLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses in FastAPI applications.
    """

    def __init__(self, app: ASGIApp, dispatch: DispatchFunction | None = None) -> None:
        super().__init__(app=app, dispatch=dispatch)
        # Get log level from the environment variable
        self._log_all_requests: bool = OidcEnvironmentVariables.str2bool(
            os.getenv("LOG_ALL_REQUESTS", "false")
        )

    async def _log_streaming_body(
        self,
        body_iterator: AsyncIterable[str | bytes | memoryview],
        request_id: str,
        request: Request,
        start_time: float,
    ) -> AsyncIterator[str | bytes | memoryview]:
        """
        Wrapper for streaming body that logs each chunk as it's yielded.

        Args:
            body_iterator: The original body iterator
            request_id: The request ID for correlation
            request: The original request
            start_time: When the request started

        Yields:
            bytes: Each chunk from the original iterator
        """
        chunk_count = 0
        total_bytes = 0

        try:
            chunk: str | bytes | memoryview
            async for chunk in body_iterator:
                chunk_count += 1
                chunk_size = len(chunk) if chunk else 0
                total_bytes += chunk_size

                # Decode chunk for logging (handle both bytes and string)
                chunk_text = chunk.decode() if isinstance(chunk, bytes) else str(chunk)

                # Log each SSE event as it's streamed
                elapsed_time = time.perf_counter() - start_time
                log_message = (
                    f"SSE Stream [{request_id}] Chunk #{chunk_count} | "
                    f"Size: {chunk_size} bytes | "
                    f"Elapsed: {elapsed_time:.4f}s | "
                    f"Content: {chunk_text[:500]}{'...' if len(chunk_text) > 500 else ''}"
                )
                if self._log_all_requests:
                    logger.info(log_message)
                else:
                    logger.debug(log_message)

                yield chunk

        except Exception as e:
            logger.error(f"SSE Stream [{request_id}] Error: {e}")
            raise
        finally:
            # Log summary when stream completes
            total_time = time.perf_counter() - start_time
            log_message = (
                f"SSE Stream [{request_id}] Completed | "
                f"Total chunks: {chunk_count} | "
                f"Total bytes: {total_bytes} | "
                f"Total time: {total_time:.4f}s"
            )
            if self._log_all_requests:
                logger.info(log_message)
            else:
                logger.debug(log_message)

    @override
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Log the request and response details.

        Args:
            request (Request): The incoming request.
            call_next (Callable): The next middleware or endpoint to call.

        Returns:
            Response: The response from the endpoint.
        """

        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex

        # don't log health check requests
        if request.url.path == "/health":
            return await call_next(request)

        try:
            req_body = await request.json()
        except Exception as ex:
            logger.warning(f"Failed to parse request body: {ex}")
            req_body = None

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time = time.perf_counter() - start_time
        # convert process_time to seconds
        process_time_in_secs = f"{process_time:.4f} secs"

        res_body_text: str = "No body"

        # Check if this is a streaming response (SSE or other streaming content)
        if "body_iterator" in response.__dict__:
            response1: StreamingResponse = cast(StreamingResponse, response)

            # Check if this is an SSE stream by looking at content-type
            content_type = response1.headers.get("content-type", "")
            is_sse = "text/event-stream" in content_type

            if is_sse:
                # For SSE, log each event as it's streamed
                log_message = (
                    f"HTTP Request [{request_id}]: {request.method} | url: {request.url} | "
                    f"Headers: {request.headers} | Body: {req_body}"
                    f"\nHTTP Response [{request_id}]: {response.status_code} | "
                    f"time: {process_time_in_secs} | Type: SSE Stream (logging chunks as they stream)"
                )
                if self._log_all_requests:
                    logger.info(log_message)
                else:
                    logger.debug(log_message)

                # Wrap the body iterator to log each chunk
                response1.body_iterator = self._log_streaming_body(
                    response1.body_iterator,
                    request_id,
                    request,
                    start_time,
                )

                return response1
            else:
                # For non-SSE streaming responses, use the original logic
                res_body: list[str | bytes | memoryview] = [
                    section async for section in response1.body_iterator
                ]
                response1.body_iterator = iterate_in_threadpool(iter(res_body))
                if len(res_body) > 0:
                    # Turn a response body object to string
                    res_body_ = res_body[0]
                    res_body_text = (
                        res_body_.decode()
                        if isinstance(res_body_, bytes)
                        else str(res_body_)
                    )
        else:
            if response.body:
                # For regular responses, we can access the body directly
                res_body2: list[bytes | memoryview] = [response.body]
                # Turn a response body object to string
                if len(res_body2) > 0:
                    res_body_2 = res_body2[0]
                    res_body_text = (
                        res_body_2.decode()
                        if isinstance(res_body_2, bytes)
                        else str(res_body_2)
                    )

        if response.status_code >= 300:
            logger.error(
                f"HTTP Request [{request_id}]: {request.method} | url: {request.url} | Headers: {request.headers} | Body: {req_body}"
                f"\nHTTP Response [{request_id}]: {response.status_code} | time: {process_time_in_secs} | Body: {res_body_text} "
            )
        elif self._log_all_requests:
            logger.info(
                f"HTTP Request [{request_id}]: {request.method} | url: {request.url} | Headers: {request.headers} | Body: {req_body}"
                f"\nHTTP Response [{request_id}]: {response.status_code} | time: {process_time_in_secs} | Body: {res_body_text} "
            )
        else:
            logger.debug(
                f"HTTP Request [{request_id}]: {request.method} | url: {request.url} | Headers: {request.headers} | Body: {req_body}"
                f"\nHTTP Response [{request_id}]: {response.status_code} | time: {process_time_in_secs} | Body: {res_body_text} "
            )
        return response