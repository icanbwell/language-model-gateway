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


def _bedrock_credential_error_detail(exc: BaseException) -> tuple[str, str] | None:
    """If `exc` (or its cause/context) is a Bedrock-credentials failure,
    return `(error_type, actionable_client_message)` for it — else None.

    Previously only `TokenRetrievalError` (expired SSO session) got this
    treatment; any other credential failure — no profile/role configured at
    all, or an STS/SSO API error surfaced as `botocore.ClientError` — fell
    through to the generic handler with an unhelpful `error_type` (e.g.
    "RuntimeError") and no actionable fix for the user.
    """
    from botocore.exceptions import ClientError, NoCredentialsError, TokenRetrievalError

    profile = os.environ.get("AWS_PROFILE", "<profile>")
    for candidate in (exc, exc.__cause__, exc.__context__):
        if isinstance(candidate, TokenRetrievalError):
            return (
                "bedrock_session_expired",
                f"AWS Bedrock session expired. Run: aws sso login --profile {profile}",
            )
        if isinstance(
            candidate, (NoCredentialsError, BedrockCredentialsUnavailableError)
        ):
            return (
                "bedrock_no_credentials",
                f"No AWS credentials configured (profile={profile}). Set "
                "AWS_PROFILE or configure a default AWS profile/role.",
            )
        if isinstance(candidate, ClientError):
            return ("bedrock_credential_error", f"AWS credential error: {candidate}")
    return None


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
