"""
Native Bedrock Converse API transport — an alternative to Bedrock Mantle's
OpenAI-compatible endpoint for auth="aws" routes, toggled by
CodingModelRouter._bedrock_transport ("mantle" default / "native").

Kept separate from bedrock_client.py (httpx passthrough + retry helpers for
the Mantle/Anthropic-passthrough paths) and aws_auth.py (SigV4 signing,
credential-error mapping for those same paths) — this module owns the boto3
bedrock-runtime client and the Anthropic/OpenAI <-> Converse format
conversions, which are a distinct concern from either.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from .bedrock_client import _TRANSIENT_STREAM_ERROR_CODES

_CLIENT_CACHE: dict[tuple[str | None, str], Any] = {}
_CLIENT_CACHE_LOCK = threading.Lock()


def _get_bedrock_runtime_client(route: dict[str, Any]) -> Any:
    """Return a cached boto3 bedrock-runtime client for this route's
    (AWS_PROFILE, region) pair. boto3 clients are thread-safe and reusable,
    so one is built per pair, not per request — mirrors the credential
    resolution in aws_auth.py's _sign_bedrock, which also keys off
    AWS_PROFILE and the route's aws_region.
    """
    import boto3

    profile = os.environ.get("AWS_PROFILE")
    region = route.get("aws_region", "us-east-1")
    key = (profile, region)
    if key not in _CLIENT_CACHE:
        with _CLIENT_CACHE_LOCK:
            if key not in _CLIENT_CACHE:
                session = (
                    boto3.Session(profile_name=profile) if profile else boto3.Session()
                )
                _CLIENT_CACHE[key] = session.client(
                    "bedrock-runtime", region_name=region
                )
    return _CLIENT_CACHE[key]


def _is_transient_bedrock_error_code(code: str | None) -> bool:
    """Whether a native Bedrock ClientError's Error.Code is worth retrying
    with backoff — reuses the same exception-name taxonomy already applied
    to Bedrock Mantle's mid-stream errors in bedrock_client.py, since these
    are the same underlying Bedrock exception names either way.
    """
    return code in _TRANSIENT_STREAM_ERROR_CODES
