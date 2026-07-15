"""
Native Bedrock Converse API client lifecycle — an alternative to Bedrock
Mantle's OpenAI-compatible endpoint for auth="aws" routes, toggled by
CodingModelRouter._bedrock_transport ("mantle" default / "native").

This module owns only two things now:
  - BedrockRuntimeClientProvider: caching/lifecycle of the boto3
    bedrock-runtime client per (AWS_PROFILE, region) pair.
  - _is_transient_bedrock_error_code: classification of native Bedrock
    ClientError codes for retry/backoff purposes.

Request/response translation between the OpenAI-Chat-Completions shape and
Bedrock Converse's shape now lives in converse_request_translator.py, and
streaming adaptation (Converse event stream -> Anthropic SSE) lives in
converse_stream_adapter.py — both were split out of this module to keep it
focused on client lifecycle and error classification.

Kept separate from bedrock_client.py (httpx passthrough + retry helpers for
the Mantle/Anthropic-passthrough paths) and aws_auth.py (SigV4 signing,
credential-error mapping for those same paths) — this module's concerns
(boto3 client caching, native error-code classification) are distinct from
either.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Literal, cast

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .bedrock_client import _TRANSIENT_STREAM_ERROR_CODES

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))


class BedrockRuntimeClientProvider:
    """Caches boto3 bedrock-runtime clients per (AWS_PROFILE, region) pair.
    boto3 clients are thread-safe and reusable, so one is built per pair,
    not per request — mirrors the credential resolution in aws_auth.py's
    _sign_bedrock, which also keys off AWS_PROFILE and the route's aws_region.

    `connect_timeout_seconds`/`read_timeout_seconds` are passed explicitly
    to botocore's Config rather than left to its built-in defaults (60s/60s)
    — a long streamed generation (large max_tokens, slow model) can exceed
    that on a single read, surfacing as a generic "Read timed out" error with
    no way to tune it short of a code change. See
    LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_connect_timeout_seconds
    / model_routing_bedrock_read_timeout_seconds for the env vars that
    control these in CodingModelRouter.

    `max_attempts`/`retry_mode` mirror languagemodelcommon's
    AwsClientFactory.create_bedrock_client (used by the general
    chat-completions path, a separate Bedrock client from this one) —
    defaulting max_attempts to 1 there and here is deliberate, not an
    oversight: CodingModelRouter already retries transient native-Bedrock
    errors itself with its own backoff (see _throttle_backoff /
    _is_transient_bedrock_error_code in router.py). Raising max_attempts
    above 1 stacks botocore's own retry/backoff on top of that outer loop,
    so only do so with that interaction in mind.

    `tcp_keepalive=True` (also mirroring AwsClientFactory) enables TCP
    keepalive probes on the underlying socket, so a genuinely dead
    connection is detected via keepalive rather than only via the read
    timeout above.
    """

    def __init__(
        self,
        *,
        connect_timeout_seconds: float = 60.0,
        read_timeout_seconds: float = 60.0,
        max_attempts: int = 1,
        retry_mode: str = "adaptive",
    ) -> None:
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._max_attempts = max_attempts
        self._retry_mode = retry_mode
        self._cache: dict[tuple[str | None, str], Any] = {}
        self._lock = threading.Lock()

    def get_client(self, route: dict[str, Any]) -> Any:
        import boto3
        from botocore.config import Config

        profile = os.environ.get("AWS_PROFILE")
        region = route.get("aws_region", "us-east-1")
        key = (profile, region)
        if key not in self._cache:
            with self._lock:
                if key not in self._cache:
                    session = (
                        boto3.Session(profile_name=profile)
                        if profile
                        else boto3.Session()
                    )
                    self._cache[key] = session.client(
                        "bedrock-runtime",
                        region_name=region,
                        config=Config(
                            connect_timeout=self._connect_timeout_seconds,
                            read_timeout=self._read_timeout_seconds,
                            retries={
                                "max_attempts": self._max_attempts,
                                "mode": cast(
                                    Literal["legacy", "standard", "adaptive"],
                                    self._retry_mode,
                                ),
                            },
                            tcp_keepalive=True,
                        ),
                    )
        return self._cache[key]


def _is_transient_bedrock_error_code(code: str | None) -> bool:
    """Whether a native Bedrock ClientError's Error.Code is worth retrying
    with backoff — reuses the same exception-name taxonomy already applied
    to Bedrock Mantle's mid-stream errors in bedrock_client.py, since these
    are the same underlying Bedrock exception names either way.
    """
    return code in _TRANSIENT_STREAM_ERROR_CODES
