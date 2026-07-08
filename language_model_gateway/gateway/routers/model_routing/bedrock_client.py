from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .aws_auth import _sign_bedrock
from .constants import (
    _BEDROCK_MIN_DISPATCH_INTERVAL_S,
    _CONTEXT_OVERFLOW_RE,
    _MAX_THROTTLE_RETRIES,
    _THROTTLE_BASE_DELAY_S,
    _THROTTLE_MAX_DELAY_S,
    _THROTTLE_TEXT_RE,
)

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_bedrock_dispatch_lock = asyncio.Lock()
_bedrock_last_dispatch: float = 0.0


async def _pace_bedrock_dispatch() -> None:
    global _bedrock_last_dispatch
    async with _bedrock_dispatch_lock:
        loop = asyncio.get_running_loop()
        wait = _BEDROCK_MIN_DISPATCH_INTERVAL_S - (loop.time() - _bedrock_last_dispatch)
        if wait > 0:
            await asyncio.sleep(wait)
        _bedrock_last_dispatch = asyncio.get_running_loop().time()


def _throttle_backoff(attempt: int) -> float:
    ceiling = min(_THROTTLE_MAX_DELAY_S, _THROTTLE_BASE_DELAY_S * (2**attempt))
    return random.uniform(ceiling / 2, ceiling)


def _is_throttling(status_code: int, body_text: str = "") -> bool:
    # Context overflow errors (input token limits) are not retried as throttling
    # EXCEPT for 429 status codes, which explicitly indicate rate limiting.
    # A 429 with "context overflow" in the body should still be retried.
    if status_code == 429:
        return True
    # Only exclude context overflow for non-429 client errors (4xx)
    if (
        status_code >= 400
        and status_code != 429
        and _CONTEXT_OVERFLOW_RE.search(body_text or "")
    ):
        return False
    # Check body text for throttling indicators in error responses (4xx/5xx)
    if status_code >= 400 and _THROTTLE_TEXT_RE.search(body_text or ""):
        return True
    return False


async def _send_with_bedrock_retry(
    client: httpx.AsyncClient,
    target_url: str,
    upstream_headers: dict[str, str],
    raw_body: bytes,
    route: dict[str, Any],
    auth: str,
) -> httpx.Response:
    attempt = 0
    while True:
        if auth == "aws":
            await _pace_bedrock_dispatch()
        upstream_req = client.build_request(
            "POST", target_url, headers=upstream_headers, content=raw_body
        )
        resp = await client.send(upstream_req, stream=True)

        if auth != "aws" or resp.status_code < 400 or attempt >= _MAX_THROTTLE_RETRIES:
            return resp

        error_body = await resp.aread()
        await resp.aclose()
        error_text = error_body.decode("utf-8", errors="replace")

        if not _is_throttling(resp.status_code, error_text):
            return httpx.Response(
                status_code=resp.status_code, headers=resp.headers, content=error_body
            )

        delay = _throttle_backoff(attempt)
        attempt += 1
        logger.warning(
            "[coding-model-router] Bedrock throttled (attempt %d/%d): backing off %.1fs — %s",
            attempt,
            _MAX_THROTTLE_RETRIES,
            delay,
            error_text[:200],
        )
        await asyncio.sleep(delay)
        sig_headers = {
            k.lower(): v for k, v in _sign_bedrock(target_url, raw_body, route).items()
        }
        upstream_headers = {**upstream_headers, **sig_headers}
