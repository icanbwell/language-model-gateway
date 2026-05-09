import os

from fastapi import Request
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from starlette.responses import Response
from starlette.responses import RedirectResponse

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig

_DEFAULT_CLIENT_ID = "0oa11g45c90Fqbgzz698"
_DEFAULT_METADATA_URL = "https://icanbwell.okta.com/.well-known/openid-configuration"
_DEFAULT_DISPLAY_NAME = "Okta b.well"


class SkillAuthService:
    """Handles OAuth provider registration and login for the skill publisher.

    Auth configuration is read from environment variables when available,
    falling back to defaults.  The provider is registered via
    OAuthProviderRegistrar (idempotent — skips if already registered at
    startup from AUTH_PROVIDERS).
    """

    def __init__(self, *, mcp_server_gateway_url: str) -> None:
        self._mcp_server_gateway_url = mcp_server_gateway_url

        self._client_id = os.environ.get(
            "SKILLS_PUBLISHER_CLIENT_ID", _DEFAULT_CLIENT_ID
        )
        self._metadata_url = os.environ.get(
            "SKILLS_PUBLISHER_METADATA_URL", _DEFAULT_METADATA_URL
        )
        self._display_name = os.environ.get(
            "SKILLS_PUBLISHER_DISPLAY_NAME", _DEFAULT_DISPLAY_NAME
        )
        self._auth_provider = f"mcp_oauth_{self._client_id}"

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
            auth_provider=self._auth_provider,
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
            authServerMetadataUrl=self._metadata_url,
            clientId=self._client_id,
            displayName=self._display_name,
        )
        await oauth_provider_registrar.register_provider(
            auth_provider=self._auth_provider,
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
