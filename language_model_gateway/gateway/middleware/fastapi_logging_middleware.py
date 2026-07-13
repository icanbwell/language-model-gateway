import json
import logging
import time
from typing import override, Callable, Awaitable, AsyncIterator, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["HTTP_TRACING"])


class FastApiLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses in FastAPI applications.
    """

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

        # don't log health check requests
        if request.url.path == "/health":
            return await call_next(request)

        try:
            req_body = await request.json()
        except Exception:
            req_body = None

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time = time.perf_counter() - start_time
        # convert process_time to seconds
        process_time_in_secs = f"{process_time:.4f} secs"

        res_body_text: str = "No body"

        if logger.isEnabledFor(logging.DEBUG):
            content_type = response.headers.get("content-type", "")
            is_text = (
                content_type.startswith("text/")
                or content_type.startswith("application/json")
                or content_type.startswith("application/xml")
                or content_type.startswith("application/yaml")
                or content_type.startswith("application/x-www-form-urlencoded")
            )
            # If response is StreamingResponse, only log the first chunk —
            # draining the whole body_iterator here would buffer an entire
            # SSE stream in memory before any of it reaches the client,
            # defeating streaming outright (the client would wait for the
            # full upstream generation to finish before receiving anything).
            if "body_iterator" in response.__dict__:
                response1: StreamingResponse = cast(StreamingResponse, response)
                original_iterator = response1.body_iterator.__aiter__()
                try:
                    first_chunk: (
                        str | bytes | memoryview | None
                    ) = await original_iterator.__anext__()
                except StopAsyncIteration:
                    first_chunk = None

                async def _rechain() -> AsyncIterator[str | bytes | memoryview]:
                    if first_chunk is not None:
                        yield first_chunk
                    async for section in original_iterator:
                        yield section

                response1.body_iterator = _rechain()

                if first_chunk is not None:
                    if is_text:
                        res_body_text = (
                            first_chunk.decode()
                            if isinstance(first_chunk, bytes)
                            else str(first_chunk)
                        )
                    else:
                        # Safely get length if possible
                        try:
                            body_len = len(first_chunk)
                        except TypeError:
                            body_len = None
                        res_body_text = (
                            f"Non-text response: {content_type}, {body_len} bytes"
                        )
            else:
                if response.body:
                    res_body2: list[bytes | memoryview] = [response.body]
                    if len(res_body2) > 0:
                        res_body_2 = res_body2[0]
                        if is_text:
                            res_body_text = (
                                res_body_2.decode()
                                if isinstance(res_body_2, bytes)
                                else str(res_body_2)
                            )
                        else:
                            try:
                                body_len2 = len(res_body_2)
                            except TypeError:
                                body_len2 = None
                            res_body_text = (
                                f"Non-text response: {content_type}, {body_len2} bytes"
                            )

        if response.status_code >= 300:
            logger.error(
                f"\n==== Request ERROR: {request.method} {request.url} ======"
                f"\n===== Headers ======"
                f"\n{request.headers}"
                f"\n====== Request Body ====="
                f"\n{json.dumps(req_body)}"
                f"\n==== End of Request Body ======"
            )
            logger.error(
                f"\n====== Response ERROR : {response.status_code} {request.method} {request.url} (time: {process_time_in_secs}) ======"
                f"\n==== Response Body ======"
                f"\n{res_body_text}"
                f"\n==== End of Response Body ======"
            )
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"\n==== Request: {request.method} {request.url} ======"
                    f"\n===== Headers ======"
                    f"\n{request.headers}"
                    f"\n====== Request Body ====="
                    f"\n{json.dumps(req_body)}"
                    f"\n==== End of Request Body ======"
                )
                logger.debug(
                    f"\n====== Response: {response.status_code} {request.method} {request.url} (time: {process_time_in_secs}) ======"
                    f"\n==== Response Body ======"
                    f"\n{res_body_text}"
                    f"\n==== End of Response Body ======"
                )
        return response
