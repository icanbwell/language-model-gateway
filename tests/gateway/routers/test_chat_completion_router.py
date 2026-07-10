"""
Tests for ChatCompletionsRouter.read_auth_information — identity-header IDOR.

x-openwebui-user-id/x-openwebui-user-email/x-openwebui-user-name headers are
fully caller-controlled, so they must never be trusted for identity unless
the Authorization header verifies as a genuine, signature-checked OIDC
token. Trusting them otherwise lets an unauthenticated caller impersonate
any user (e.g. system_command_manager uses AuthInformation.subject as
referring_subject to delete a user's cached tokens).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from language_model_gateway.gateway.routers.chat_completion_router import (
    ChatCompletionsRouter,
)


def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def _make_environment_variables() -> MagicMock:
    environment_variables = MagicMock()
    environment_variables.auth_redirect_uri = "http://localhost/auth/callback"
    return environment_variables


@pytest.mark.asyncio
async def test_read_auth_information_no_authorization_header_ignores_identity_headers() -> (
    None
):
    """No Authorization header at all means no verified identity."""
    router = ChatCompletionsRouter()
    request = _make_request({"x-openwebui-user-id": "victim@example.com"})
    token_reader = MagicMock()

    auth_information = await router.read_auth_information(
        environment_variables=_make_environment_variables(),
        request=request,
        token_reader=token_reader,
        auth_manager=MagicMock(),
    )

    assert auth_information.subject is None
    assert auth_information.email is None
    assert auth_information.user_name is None
    token_reader.verify_token_async.assert_not_called()


@pytest.mark.asyncio
async def test_read_auth_information_invalid_token_ignores_identity_headers() -> None:
    """An Authorization header that fails verification must not fall back to
    trusting caller-controlled identity headers."""
    router = ChatCompletionsRouter()
    token_reader = MagicMock()
    token_reader.extract_token.return_value = "not-a-real-jwt"
    token_reader.verify_token_async = AsyncMock(return_value=None)
    request = _make_request(
        {
            "authorization": "Bearer not-a-real-jwt",
            "x-openwebui-user-id": "victim@example.com",
            "x-openwebui-user-email": "victim@example.com",
            "x-openwebui-user-name": "Victim",
        }
    )

    auth_information = await router.read_auth_information(
        environment_variables=_make_environment_variables(),
        request=request,
        token_reader=token_reader,
        auth_manager=MagicMock(),
    )

    assert auth_information.subject is None
    assert auth_information.email is None
    assert auth_information.user_name is None


@pytest.mark.asyncio
async def test_read_auth_information_dev_bypass_token_ignores_identity_headers() -> (
    None
):
    """The "fake-api-key"/"bedrock" local-dev bypass values must not fall
    back to trusting caller-controlled identity headers either."""
    router = ChatCompletionsRouter()
    token_reader = MagicMock()
    token_reader.extract_token.return_value = "fake-api-key"
    token_reader.verify_token_async = AsyncMock()
    request = _make_request(
        {
            "authorization": "Bearer fake-api-key",
            "x-openwebui-user-id": "victim@example.com",
        }
    )

    auth_information = await router.read_auth_information(
        environment_variables=_make_environment_variables(),
        request=request,
        token_reader=token_reader,
        auth_manager=MagicMock(),
    )

    assert auth_information.subject is None
    token_reader.verify_token_async.assert_not_called()


@pytest.mark.asyncio
async def test_read_auth_information_valid_token_uses_verified_identity_not_headers() -> (
    None
):
    """A verified token's claims are used for identity, taking precedence
    over (and ignoring) any caller-supplied identity headers."""
    router = ChatCompletionsRouter()
    verified_token = MagicMock()
    verified_token.claims = {"sub": "verified-user-123"}
    verified_token.expires = None
    verified_token.audience = "some-audience"
    verified_token.subject = "verified-user-123"
    verified_token.email = "verified@example.com"
    verified_token.name = "Verified User"

    token_reader = MagicMock()
    token_reader.extract_token.return_value = "a.valid.jwt"
    token_reader.verify_token_async = AsyncMock(return_value=verified_token)
    request = _make_request(
        {
            "authorization": "Bearer a.valid.jwt",
            "x-openwebui-user-id": "attacker-supplied-id",
            "x-openwebui-user-email": "attacker@example.com",
            "x-openwebui-user-name": "Attacker",
        }
    )

    auth_information = await router.read_auth_information(
        environment_variables=_make_environment_variables(),
        request=request,
        token_reader=token_reader,
        auth_manager=MagicMock(),
    )

    assert auth_information.subject == "verified-user-123"
    assert auth_information.email == "verified@example.com"
    assert auth_information.user_name == "Verified User"
