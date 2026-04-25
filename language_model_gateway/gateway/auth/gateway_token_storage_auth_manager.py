import logging
from typing import override, Any, Dict

from fastapi import Request
from oidcauthlib.auth.auth_helper import AuthHelper
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)
from starlette.responses import Response

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from languagemodelcommon.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from languagemodelcommon.auth.token_storage_auth_manager import TokenStorageAuthManager
from languagemodelcommon.configs.config_reader.mcp_json_fetcher import McpJsonFetcher
from languagemodelcommon.configs.config_reader.mcp_json_reader import (
    _compute_oauth_provider_key,
)
from languagemodelcommon.configs.schemas.mcp_json_schema import McpJsonConfig
from language_model_gateway.gateway.utilities.auth_success_page import (
    build_auth_success_page,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class GatewayTokenStorageAuthManager(TokenStorageAuthManager):
    """Gateway-specific TokenStorageAuthManager that renders the HTML success page.

    Overrides ``read_callback_response`` to auto-register MCP OAuth
    providers from plugin MCP configs when the auth config is not found
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
        oauth_provider_registrar: OAuthProviderRegistrar,
        mcp_json_fetcher: McpJsonFetcher | None = None,
        plugin_names: list[str] | None = None,
    ) -> None:
        super().__init__(
            environment_variables=environment_variables,
            auth_config_reader=auth_config_reader,
            token_reader=token_reader,
            token_exchange_manager=token_exchange_manager,
            well_known_configuration_manager=well_known_configuration_manager,
        )
        self._oauth_provider_registrar = oauth_provider_registrar
        self._mcp_json_fetcher = mcp_json_fetcher
        self._plugin_names = plugin_names or []

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
        """Attempt to reconstruct and register an AuthConfig from MCP config.

        Fetches plugin MCP configs from the skills server via
        ``McpJsonFetcher``, looks up the OAuth config by matching the
        ``auth_provider`` key, then delegates to
        ``OAuthProviderRegistrar.register_provider()`` for discovery,
        DCR, AuthConfig construction, and registration.
        """
        mcp_config = await self._load_mcp_config()
        if mcp_config is None:
            logger.warning(
                "Cannot auto-register auth provider '%s': no MCP config available",
                auth_provider,
            )
            return

        for server_key, entry in mcp_config.mcpServers.items():
            if not entry.oauth:
                continue
            provider_key = _compute_oauth_provider_key(server_key, entry.oauth)
            if provider_key.lower() != auth_provider.lower():
                continue

            try:
                await self._oauth_provider_registrar.register_provider(
                    auth_provider=auth_provider,
                    oauth=entry.oauth,
                    server_url=entry.url,
                    auth_manager=self,
                )
                logger.info(
                    "Auto-registered MCP OAuth provider '%s' from MCP server '%s'",
                    auth_provider,
                    server_key,
                )
            except ValueError:
                logger.error(
                    "Could not resolve client_id for '%s' from MCP server '%s'",
                    auth_provider,
                    server_key,
                    exc_info=True,
                )
            return

        logger.warning(
            "Auth provider '%s' not found in MCP config — "
            "cannot auto-register for callback",
            auth_provider,
        )

    async def _load_mcp_config(self) -> McpJsonConfig | None:
        """Load MCP config by merging all plugin configs from the fetcher.

        The auth manager needs to search across all plugin MCP configs
        to find the OAuth provider that matches the callback state.
        Since we don't know which plugin the auth provider belongs to,
        we fetch configs for all known plugins and merge them.
        """
        if not self._mcp_json_fetcher or not self._plugin_names:
            return None

        plugin_configs = await self._mcp_json_fetcher.fetch_plugins_async(
            self._plugin_names
        )
        if not plugin_configs:
            return None

        merged: dict[str, Any] = {}
        for pc in plugin_configs.values():
            merged.update(pc.mcpServers)
        return McpJsonConfig(mcpServers=merged) if merged else None

    @override
    async def get_html_response(self, access_token: str | None) -> Response:
        return build_auth_success_page(access_token)
