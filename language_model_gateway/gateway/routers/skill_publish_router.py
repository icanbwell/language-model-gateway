import os
from enum import Enum
from pathlib import Path
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Request, params
from fastapi.responses import FileResponse
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from simple_container.container.inject import Inject
from starlette.responses import Response

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from language_model_gateway.gateway.skills.skill_auth_service import SkillAuthService
from language_model_gateway.gateway.skills.skill_publish_client import (
    SkillPublishClient,
)

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


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
        mcp_server_gateway_url = os.environ.get(
            "MCP_SERVER_GATEWAY_URL", "http://mcp_server_gateway:5000"
        )
        self._auth_service = SkillAuthService(
            mcp_server_gateway_url=mcp_server_gateway_url
        )
        self._publish_client = SkillPublishClient(
            mcp_server_gateway_url=mcp_server_gateway_url
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
        """Initiate OAuth login for the skills-publisher."""
        return await self._auth_service.initiate_login(
            request=request,
            auth_manager=auth_manager,
            oauth_provider_registrar=oauth_provider_registrar,
            return_url=return_url,
        )

    async def publish_skill(self, request: Request) -> Response:
        """Proxy the publish request to the mcp-server-gateway REST API."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
            )

        body = await request.json()
        return await self._publish_client.publish(body=body, auth_header=auth_header)

    def get_router(self) -> APIRouter:
        return self.router
