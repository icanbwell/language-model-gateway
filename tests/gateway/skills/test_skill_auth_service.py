"""Tests for SkillAuthService."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI, Request

from language_model_gateway.gateway.skills.skill_auth_service import (
    SkillAuthService,
)


@pytest.fixture
def auth_service() -> SkillAuthService:
    return SkillAuthService(mcp_server_gateway_url="http://mcp-gateway:5000")


class TestSkillAuthService:
    def test_default_auth_provider_key(self, auth_service: SkillAuthService) -> None:
        assert auth_service._auth_provider == "mcp_oauth_0oa11g45c90Fqbgzz698"

    def test_custom_client_id_from_env(self) -> None:
        with patch.dict(os.environ, {"SKILLS_PUBLISHER_CLIENT_ID": "custom-id"}):
            service = SkillAuthService(mcp_server_gateway_url="http://mcp-gateway:5000")
        assert service._auth_provider == "mcp_oauth_custom-id"
        assert service._client_id == "custom-id"

    def test_custom_metadata_url_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SKILLS_PUBLISHER_METADATA_URL": "https://custom.idp/.well-known/openid-configuration"
            },
        ):
            service = SkillAuthService(mcp_server_gateway_url="http://mcp-gateway:5000")
        assert (
            service._metadata_url
            == "https://custom.idp/.well-known/openid-configuration"
        )

    @pytest.mark.asyncio
    async def test_initiate_login_registers_provider_and_redirects(
        self, auth_service: SkillAuthService
    ) -> None:
        auth_manager = MagicMock()
        auth_manager.create_authorization_url = AsyncMock(
            return_value="https://idp.example.com/authorize?state=xyz"
        )

        oauth_registrar = MagicMock()
        oauth_registrar.register_provider = AsyncMock()

        app = FastAPI()

        @app.get("/auth/callback")
        async def auth_callback() -> dict[str, str]:
            return {}

        client = TestClient(app)
        with client:
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/skills/auth/login",
                "query_string": b"return_url=/skills/publish",
                "headers": [(b"host", b"localhost")],
                "root_path": "",
                "app": app,
            }
            request = Request(scope)

            response = await auth_service.initiate_login(
                request=request,
                auth_manager=auth_manager,
                oauth_provider_registrar=oauth_registrar,
                return_url="/skills/publish",
            )

        assert response.status_code == 302
        oauth_registrar.register_provider.assert_awaited_once()
        auth_manager.create_authorization_url.assert_awaited_once()

        call_kwargs = auth_manager.create_authorization_url.call_args.kwargs
        assert call_kwargs["auth_provider"] == "mcp_oauth_0oa11g45c90Fqbgzz698"
        assert call_kwargs["url"] == "/skills/publish"

    @pytest.mark.asyncio
    async def test_ensure_provider_registered_uses_correct_server_url(
        self, auth_service: SkillAuthService
    ) -> None:
        auth_manager = MagicMock()
        oauth_registrar = MagicMock()
        oauth_registrar.register_provider = AsyncMock()

        await auth_service._ensure_provider_registered(
            auth_manager=auth_manager,
            oauth_provider_registrar=oauth_registrar,
        )

        call_kwargs = oauth_registrar.register_provider.call_args.kwargs
        assert call_kwargs["server_url"] == "http://mcp-gateway:5000/skills-publisher/"

    def test_get_auth_callback_uri_uses_env_var(self) -> None:
        with patch.dict(
            os.environ,
            {"AUTH_REDIRECT_URI": "https://gateway.example.com/auth/callback"},
        ):
            app = FastAPI()
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/skills/auth/login",
                "query_string": b"",
                "headers": [],
                "root_path": "",
                "app": app,
            }
            request = Request(scope)
            result = SkillAuthService._get_auth_callback_uri(request)
        assert result == "https://gateway.example.com/auth/callback"
