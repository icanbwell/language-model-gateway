import logging
from typing import override, Any, Dict

from fastapi import Request
from oidcauthlib.auth.auth_helper import AuthHelper
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.dcr.dcr_manager import DcrManager
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)
from starlette.responses import Response

from languagemodelcommon.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from languagemodelcommon.auth.token_storage_auth_manager import TokenStorageAuthManager
from languagemodelcommon.configs.config_reader.mcp_json_reader import (
    read_mcp_json,
    _compute_oauth_provider_key,
)
from languagemodelcommon.configs.schemas.mcp_json_schema import McpJsonConfig
from languagemodelcommon.mcp.auth.auth_server_metadata_discovery import (
    McpAuthServerDiscoveryProtocol,
)
from language_model_gateway.gateway.utilities.auth_success_page import (
    build_auth_success_page,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class GatewayTokenStorageAuthManager(TokenStorageAuthManager):
    """Gateway-specific TokenStorageAuthManager that renders the HTML success page.

    Overrides ``read_callback_response`` to auto-register MCP OAuth
    providers from ``.mcp.json`` when the auth config is not found
    in memory (e.g. after a server restart between the OAuth redirect
    and callback).
    """

    def __init__(
        self,
        *,
        environment_variables: AbstractEnvironmentVariables,
        auth_config_reader: AuthConfigReader,
        token_reader: TokenReader,
        token_exchange_manager: TokenExchangeManager,
        well_known_configuration_manager: WellKnownConfigurationManager,
        dcr_manager: DcrManager | None = None,
        auth_server_metadata_discovery: McpAuthServerDiscoveryProtocol | None = None,
    ) -> None:
        super().__init__(
            environment_variables=environment_variables,
            auth_config_reader=auth_config_reader,
            token_reader=token_reader,
            token_exchange_manager=token_exchange_manager,
            well_known_configuration_manager=well_known_configuration_manager,
        )
        self._dcr_manager = dcr_manager
        self._auth_server_metadata_discovery = auth_server_metadata_discovery

    @override
    async def read_callback_response(self, *, request: Request) -> Response:
        state: str | None = request.query_params.get("state")
        if state:
            state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
            auth_provider: str | None = state_decoded.get("auth_provider")
            if auth_provider and not self.get_auth_config_for_auth_provider(
                auth_provider=auth_provider
            ):
                await self._try_register_from_mcp_json(auth_provider)
        return await super().read_callback_response(request=request)

    async def _try_register_from_mcp_json(self, auth_provider: str) -> None:
        """Attempt to reconstruct and register an AuthConfig from .mcp.json.

        For providers with a pre-configured ``client_id``, the provider key
        follows the pattern ``mcp_oauth_{client_id}``.  For DCR providers
        (no ``client_id``), the provider key is the server key itself (e.g.
        ``"atlassian"``).

        DCR entries require ``DcrManager`` and ``McpAuthServerDiscovery``
        to perform endpoint discovery and dynamic client registration.
        """
        mcp_config: McpJsonConfig | None = read_mcp_json()
        if mcp_config is None:
            logger.warning(
                "Cannot auto-register auth provider '%s': .mcp.json not found",
                auth_provider,
            )
            return

        for server_key, entry in mcp_config.mcpServers.items():
            if not entry.oauth:
                continue
            provider_key = _compute_oauth_provider_key(server_key, entry.oauth)
            if provider_key.lower() != auth_provider.lower():
                continue

            oauth = entry.oauth

            # For DCR entries (no client_id), we need discovery + DCR
            # to obtain the client_id before we can build an AuthConfig.
            client_id = oauth.client_id
            client_secret = oauth.client_secret
            registration_url = oauth.registration_url

            if not client_id:
                if not self._dcr_manager or not self._auth_server_metadata_discovery:
                    logger.warning(
                        "Auth provider '%s' requires DCR but dcr_manager or "
                        "auth_server_metadata_discovery is not configured",
                        auth_provider,
                    )
                    return

                # Discover OAuth endpoints from the MCP server URL
                if entry.url and not oauth.authorization_url:
                    logger.info(
                        "Discovering auth server metadata for '%s' from %s",
                        auth_provider,
                        entry.url,
                    )
                    discovered = await self._auth_server_metadata_discovery.discover(
                        mcp_server_url=entry.url,
                    )
                    if discovered is not None:
                        if discovered.registration_url:
                            registration_url = discovered.registration_url
                        if discovered.authorization_url and not oauth.authorization_url:
                            oauth.authorization_url = discovered.authorization_url
                        if discovered.token_url and not oauth.token_url:
                            oauth.token_url = discovered.token_url
                        if discovered.issuer and not oauth.issuer:
                            oauth.issuer = discovered.issuer
                        if discovered.scopes and not oauth.scopes:
                            oauth.scopes = discovered.scopes

                # Perform DCR to get a client_id
                dcr_client_name: str | None = (
                    (
                        oauth.client_metadata.client_name
                        if oauth.client_metadata
                        else None
                    )
                    or oauth.display_name
                    or auth_provider
                )
                dcr_result = await self._dcr_manager.resolve_dcr_credentials(
                    auth_provider=auth_provider,
                    registration_url=registration_url,
                    client_id=None,
                    client_name=dcr_client_name,
                    client_uri=(
                        oauth.client_metadata.client_uri
                        if oauth.client_metadata
                        else None
                    ),
                    logo_uri=(
                        oauth.client_metadata.logo_uri
                        if oauth.client_metadata
                        else None
                    ),
                    contacts=(
                        oauth.client_metadata.contacts
                        if oauth.client_metadata
                        else None
                    ),
                )
                if dcr_result is not None:
                    client_id = dcr_result.client_id
                    client_secret = dcr_result.client_secret

                if not client_id:
                    logger.error(
                        "Could not resolve client_id for '%s' via DCR "
                        "(registration_url=%s)",
                        auth_provider,
                        registration_url,
                    )
                    return

            auth_config = AuthConfig(
                auth_provider=auth_provider,
                friendly_name=oauth.display_name or server_key,
                audience=oauth.audience or client_id,
                issuer=oauth.issuer,
                client_id=client_id,
                client_secret=client_secret,
                well_known_uri=oauth.auth_server_metadata_url,
                scope=oauth.scope_string,
                authorization_endpoint=oauth.authorization_url,
                token_endpoint=oauth.token_url,
                use_pkce=oauth.use_pkce,
                pkce_method=oauth.pkce_method,
                registration_url=registration_url,
            )

            self.auth_config_reader.register_auth_configs(configs=[auth_config])
            await self.register_dynamic_provider(auth_config=auth_config)

            logger.info(
                "Auto-registered MCP OAuth provider '%s' (client_id=%s) "
                "from .mcp.json server '%s'",
                auth_provider,
                client_id,
                server_key,
            )
            return

        logger.warning(
            "Auth provider '%s' not found in .mcp.json — "
            "cannot auto-register for callback",
            auth_provider,
        )

    @override
    async def get_html_response(self, access_token: str | None) -> Response:
        return build_auth_success_page(access_token)
