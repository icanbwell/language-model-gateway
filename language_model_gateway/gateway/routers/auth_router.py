import logging
import os
from typing import Any, Dict, cast

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from language_model_gateway.gateway.auth.auth_helper import AuthHelper
from language_model_gateway.gateway.auth.oauth_cache import OAuthCache

logger = logging.getLogger(__name__)


class AuthRouter:
    def __init__(self) -> None:
        # OIDC PKCE setup
        self.auth_provider_name = os.getenv("AUTH_PROVIDER_NAME")
        self.well_known_url = os.getenv("AUTH_WELL_KNOWN_URI")
        self.client_id = os.getenv("AUTH_CLIENT_ID")
        self.client_secret = os.getenv("AUTH_CLIENT_SECRET")
        self.redirect_uri = os.getenv("AUTH_REDIRECT_URI")
        # session_secret = os.getenv("AUTH_SESSION_SECRET")
        assert self.auth_provider_name is not None, (
            "AUTH_PROVIDER_NAME environment variable must be set"
        )
        assert self.well_known_url is not None, (
            "AUTH_WELL_KNOWN_URI environment variable must be set"
        )
        assert self.client_id is not None, (
            "AUTH_CLIENT_ID environment variable must be set"
        )
        assert self.client_secret is not None, (
            "AUTH_CLIENT_SECRET environment variable must be set"
        )
        assert self.redirect_uri is not None, (
            "AUTH_REDIRECT_URI environment variable must be set"
        )
        # assert session_secret is not None, (
        #     "AUTH_SESSION_SECRET environment variable must be set"
        # )

        # https://docs.authlib.org/en/latest/client/frameworks.html#frameworks-clients
        cache: OAuthCache = OAuthCache()
        self.oauth: OAuth = OAuth(cache=cache)
        self.oauth.register(
            name=self.auth_provider_name,
            client_id=self.client_id,
            client_secret=self.client_secret,
            server_metadata_url=self.well_known_url,
            client_kwargs={"scope": "openid email", "code_challenge_method": "S256"},
        )

        self.router = APIRouter()
        self.router.add_api_route("/auth/login", self.login, methods=["GET"])
        self.router.add_api_route("/auth/callback", self.auth_callback, methods=["GET"])

    async def login(self, request: Request) -> RedirectResponse:
        logger.info(f"Received request for auth login: {request.url}")
        redirect_uri1 = request.url_for("auth_callback")
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state_content = {
            "tool_name": "auth",
        }
        # convert state_content to a string
        state: str = AuthHelper.encode_state(state_content)

        # https://docs.authlib.org/en/latest/client/api.html
        return cast(
            RedirectResponse,
            await client.authorize_redirect(
                request=request,
                redirect_uri=redirect_uri1,
                state=state,
            ),
        )

    async def auth_callback(self, request: Request) -> JSONResponse:
        logger.info(f"Received request for auth callback: {request.url}")
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state: str | None = request.query_params.get("state")
        code: str | None = request.query_params.get("code")
        assert state is not None, "State must be provided in the callback"
        state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
        logger.info(f"State decoded: {state_decoded}")
        logger.info(f"Code received: {code}")
        token = await client.authorize_access_token(request)
        access_token = token["access_token"]
        assert access_token is not None, (
            "access_token was not found in the token response"
        )
        # auth_token_exchange_client_id = os.getenv("AUTH_TOKEN_EXCHANGE_CLIENT_ID")
        # assert auth_token_exchange_client_id is not None, (
        #     "AUTH_TOKEN_EXCHANGE_CLIENT_ID environment variable must be set"
        # )
        return JSONResponse(
            {
                "token": token,
                "state": state_decoded,
                "code": code,
            }
        )

    def get_router(self) -> APIRouter:
        """ """
        return self.router
