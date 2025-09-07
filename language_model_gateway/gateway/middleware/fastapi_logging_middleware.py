import logging
import time
from typing import override, Callable, Awaitable, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.concurrency import iterate_in_threadpool

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
        # if response is StreamingResponse, we need to read the body
        if "body_iterator" in response.__dict__:
            response1: StreamingResponse = cast(StreamingResponse, response)
            res_body: list[str | bytes | memoryview] = [
                section async for section in response1.body_iterator
            ]
            response1.body_iterator = iterate_in_threadpool(iter(res_body))
            if len(res_body) > 0:
                # Turn response body object to string
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
                # Turn response body object to string
                if len(res_body2) > 0:
                    res_body_2 = res_body2[0]
                    res_body_text = (
                        res_body_2.decode()
                        if isinstance(res_body_2, bytes)
                        else str(res_body_2)
                    )

        if response.status_code >= 300:
            logger.error(
                f"Request: {request.method} {request.url} | Headers: {request.headers} | Body: {req_body}"
            )
            logger.error(
                f"Response: {response.status_code} | {request.method} {request.url} | time: {process_time_in_secs} | Body: {res_body_text} "
            )
        else:
            logger.debug(
                f"Request: {request.method} {request.url} | Headers: {request.headers} | Response Body: {req_body}"
            )
            logger.debug(
                f"Response: {response.status_code} | {request.method} {request.url} | time: {process_time_in_secs} | Response Body: {res_body_text} "
            )
        return response
