import logging
from typing import Any, AsyncIterator

import httpx

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["HTTP"])


class LoggingResponse(httpx.Response):
    """
    A custom HTTP response class that logs the request and response details.
    This class extends httpx.Response to log the request method, URL, status code,
    and response content in bytes as they are streamed.
    """

    async def aiter_bytes(self, *args: Any, **kwargs: Any) -> AsyncIterator[bytes]:
        """
        Asynchronously iterate over the response content in bytes, logging each chunk.
        This method overrides the default aiter_bytes method to include logging.
        Args:
            *args: Positional arguments passed to the parent method.
            **kwargs: Keyword arguments passed to the parent method.
        Yields:
            bytes: The next chunk of response content in bytes.
        """
        logger.debug(
            f"====== Response: {self.request.method} {self.url} {self.status_code} ====="
        )
        async for chunk in super().aiter_bytes(*args, **kwargs):
            logger.debug(chunk)
            yield chunk
        logger.debug(
            f"====== End Response: {self.request.method} {self.url} {self.status_code} ====="
        )
