from __future__ import annotations

import os
from typing import Any, Generator, override

import httpx


class BedrockCredentialsUnavailableError(RuntimeError):
    """No AWS credentials are configured at all (no profile/role found).

    Distinct from botocore's TokenRetrievalError (an expired SSO session) —
    this is "nothing to refresh", not "refresh needed" — so callers can give
    a different, actionable message for each.
    """


def _sign_bedrock(url: str, body: bytes, route: dict[str, Any]) -> dict[str, str]:
    """Return headers dict with AWS SigV4 Authorization for a Bedrock POST."""
    import boto3
    from botocore.auth import SigV4Auth as _BotocoreSigV4Auth
    from botocore.awsrequest import AWSRequest

    profile = os.environ.get("AWS_PROFILE")
    region = route.get("aws_region", "us-east-1")
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    raw_creds = session.get_credentials()
    if raw_creds is None:
        raise BedrockCredentialsUnavailableError("No AWS credentials available")
    creds = raw_creds.get_frozen_credentials()
    req = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    _BotocoreSigV4Auth(creds, "bedrock", region).add_auth(req)
    return dict(req.headers)


class SigV4Auth(httpx.Auth):
    """Apply AWS SigV4 signing per request via httpx.Auth (used by openai SDK transport)."""

    def __init__(self, route: dict[str, Any]) -> None:
        self._route = route

    @override
    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        signed = _sign_bedrock(str(request.url), request.content, self._route)
        for k, v in signed.items():
            request.headers[k.lower()] = v
        yield request
