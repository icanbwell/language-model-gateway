import logging
import os
from enum import Enum
from pathlib import Path
from typing import Annotated, Sequence

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, params
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from simple_container.container.inject import Inject
from starlette.responses import Response

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

_SKILLS_PUBLISHER_CLIENT_ID = "0oa11g45c90Fqbgzz698"
_SKILLS_PUBLISHER_AUTH_PROVIDER = f"mcp_oauth_{_SKILLS_PUBLISHER_CLIENT_ID}"
_OKTA_METADATA_URL = "https://icanbwell.okta.com/.well-known/openid-configuration"


class SkillPublishRouter:
    """Router for the skill publish UI and its auth + publish endpoints."""

    def __init__(
        self,
        *,
        prefix: str = "/skills",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["skills"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags,
            dependencies=self.dependencies,
        )
        self._mcp_server_gateway_url = os.environ.get(
            "MCP_SERVER_GATEWAY_URL", "http://mcp_server_gateway:5000"
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/publish",
            self.render_form,
            methods=["GET"],
            response_class=FileResponse,
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/auth/login",
            self.auth_login,
            methods=["GET"],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/publish",
            self.publish_skill,
            methods=["POST"],
            include_in_schema=True,
        )

    async def render_form(self) -> FileResponse:
        """Serve the skill submission page."""
        return FileResponse(
            path=_STATIC_DIR / "skill_publish.html", media_type="text/html"
        )

    async def auth_login(
        self,
        request: Request,
        auth_manager: Annotated[
            FastAPIAuthManager, Depends(Inject(FastAPIAuthManager))
        ],
        oauth_provider_registrar: Annotated[
            OAuthProviderRegistrar, Depends(Inject(OAuthProviderRegistrar))
        ],
        return_url: str = Query(default="/skills/publish"),
    ) -> Response:
        """Initiate OAuth login for the skills-publisher.

        Redirects to Okta with state containing return_url so that the
        callback handler renders the sessionStorage template.
        """
        await self._ensure_provider_registered(
            auth_manager=auth_manager,
            oauth_provider_registrar=oauth_provider_registrar,
        )

        redirect_uri = self._get_auth_callback_uri(request)

        url = await auth_manager.create_authorization_url(
            auth_provider=_SKILLS_PUBLISHER_AUTH_PROVIDER,
            redirect_uri=redirect_uri,
            url=return_url,
            referring_email="skill-submit-ui",
            referring_subject="skill-submit-ui",
        )

        return RedirectResponse(url, status_code=302)

    async def publish_skill(self, request: Request) -> Response:
        """Proxy the publish request to the mcp-server-gateway REST API."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
            )

        body = await request.json()
        rest_url = f"{self._mcp_server_gateway_url}/api/skills/publish"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(rest_url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Network error: {exc}"},
                )

        return JSONResponse(
            status_code=response.status_code,
            content=response.json(),
        )

    async def _ensure_provider_registered(
        self,
        *,
        auth_manager: FastAPIAuthManager,
        oauth_provider_registrar: OAuthProviderRegistrar,
    ) -> None:
        """Ensure the skills-publisher OAuth provider is registered."""
        oauth_config = McpOAuthConfig(
            authServerMetadataUrl=_OKTA_METADATA_URL,
            clientId=_SKILLS_PUBLISHER_CLIENT_ID,
            displayName="Okta b.well",
        )
        await oauth_provider_registrar.register_provider(
            auth_provider=_SKILLS_PUBLISHER_AUTH_PROVIDER,
            oauth=oauth_config,
            server_url=f"{self._mcp_server_gateway_url}/skills-publisher/",
            auth_manager=auth_manager,
        )

    @staticmethod
    def _get_auth_callback_uri(request: Request) -> str:
        """Return the redirect_uri for the OAuth callback (existing endpoint)."""
        auth_redirect_uri = os.environ.get("AUTH_REDIRECT_URI")
        if auth_redirect_uri:
            return auth_redirect_uri
        return str(request.url_for("auth_callback"))

    def get_router(self) -> APIRouter:
        return self.router
