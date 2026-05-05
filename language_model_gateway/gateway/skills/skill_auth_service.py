import os

from fastapi import Request
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from starlette.responses import Response
from starlette.responses import RedirectResponse

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig

_SKILLS_PUBLISHER_CLIENT_ID = "0oa11g45c90Fqbgzz698"
_SKILLS_PUBLISHER_AUTH_PROVIDER = f"mcp_oauth_{_SKILLS_PUBLISHER_CLIENT_ID}"
_OKTA_METADATA_URL = "https://icanbwell.okta.com/.well-known/openid-configuration"


class SkillAuthService:
    """Handles OAuth provider registration and login for the skill publisher."""

    def __init__(self, *, mcp_server_gateway_url: str) -> None:
        self._mcp_server_gateway_url = mcp_server_gateway_url

    async def initiate_login(
        self,
        *,
        request: Request,
        auth_manager: FastAPIAuthManager,
        oauth_provider_registrar: OAuthProviderRegistrar,
        return_url: str,
    ) -> Response:
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

    async def _ensure_provider_registered(
        self,
        *,
        auth_manager: FastAPIAuthManager,
        oauth_provider_registrar: OAuthProviderRegistrar,
    ) -> None:
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
        auth_redirect_uri = os.environ.get("AUTH_REDIRECT_URI")
        if auth_redirect_uri:
            return auth_redirect_uri
        return str(request.url_for("auth_callback"))
