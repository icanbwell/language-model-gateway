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


# Bedrock's own streaming API (ConverseStream/InvokeModelWithResponseStream)
# documents these exception names as transient — network blips or momentary
# model overload that succeed on retry — as opposed to e.g. ValidationException
# or a content-policy failure, which fail identically every time.
_TRANSIENT_STREAM_ERROR_CODES = frozenset(
    {
        "ModelStreamErrorException",
        "ModelTimeoutException",
        "InternalServerException",
        "ServiceUnavailableException",
        "ThrottlingException",
    }
)


def _is_transient_stream_error(
    code: str | None, type_: str | None, text: str = ""
) -> bool:
    """Whether a mid-stream Bedrock error (no HTTP status code attached, so
    `_is_throttling` doesn't apply) is worth retrying.

    Covers `openai.APIError` raised by the SDK for SSE `{"error": {...}}`
    events — Bedrock Mantle's way of surfacing a stream-level failure instead
    of a 4xx/5xx response.
    """
    if code in _TRANSIENT_STREAM_ERROR_CODES or type_ in _TRANSIENT_STREAM_ERROR_CODES:
        return True
    return bool(_THROTTLE_TEXT_RE.search(text or ""))


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
    request_id: str = "unknown",
) -> httpx.Response:
    attempt = 0
    while True:
        if auth == "aws":
            await _pace_bedrock_dispatch()
        upstream_req = client.build_request(
            "POST", target_url, headers=upstream_headers, content=raw_body
        )
        try:
            resp = await client.send(upstream_req, stream=True)
        except httpx.TransportError as exc:
            # Connection-level failures (timeout, connection reset, DNS) had
            # no retry at all here — a momentary network blip failed the
            # request outright instead of getting the same backoff treatment
            # as an HTTP-level throttle response.
            if auth != "aws" or attempt >= _MAX_THROTTLE_RETRIES:
                raise
            delay = _throttle_backoff(attempt)
            attempt += 1
            logger.warning(
                "[coding-model-router] request_id=%s Bedrock transport error "
                "(attempt %d/%d): backing off %.1fs — %s: %s",
                request_id,
                attempt,
                _MAX_THROTTLE_RETRIES,
                delay,
                type(exc).__name__,
                exc,
            )
            await asyncio.sleep(delay)
            sig_headers = {
                k.lower(): v
                for k, v in _sign_bedrock(target_url, raw_body, route).items()
            }
            upstream_headers = {**upstream_headers, **sig_headers}
            continue

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
        # Include status code and truncated error for debugging
        logger.warning(
            "[coding-model-router] request_id=%s Bedrock throttled (attempt %d/%d): status=%d backing off %.1fs — %s",
            request_id,
            attempt,
            _MAX_THROTTLE_RETRIES,
            resp.status_code,
            delay,
            error_text[:200],
        )
        await asyncio.sleep(delay)
        sig_headers = {
            k.lower(): v for k, v in _sign_bedrock(target_url, raw_body, route).items()
        }
        upstream_headers = {**upstream_headers, **sig_headers}
