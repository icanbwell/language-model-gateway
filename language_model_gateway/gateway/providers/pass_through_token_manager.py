import logging
from typing import Any, Dict, List, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from oidcauthlib.auth.auth_helper import AuthHelper
from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.dcr.dcr_manager import DcrManager
from oidcauthlib.auth.models.auth import AuthInformation

from languagemodelcommon.configs.schemas.config_schema import (
    AgentConfig,
    ChatModelConfig,
    AuthenticationConfig,
    McpOAuthConfig,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class PassThroughTokenManager:
    def __init__(
        self,
        *,
        auth_manager: AuthManager,
        auth_config_reader: AuthConfigReader,
        tool_auth_manager: ToolAuthManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        dcr_manager: DcrManager,
    ) -> None:
        self.auth_manager: AuthManager = auth_manager
        if self.auth_manager is None:
            raise ValueError("auth_manager must not be None")
        if not isinstance(self.auth_manager, AuthManager):
            raise TypeError("auth_manager must be an instance of AuthManager")

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )

        self.tool_auth_manager: ToolAuthManager = tool_auth_manager
        if self.tool_auth_manager is None:
            raise ValueError("tool_auth_manager must not be None")
        if not isinstance(self.tool_auth_manager, ToolAuthManager):
            raise TypeError("tool_auth_manager must be an instance of ToolAuthManager")

        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "environment_variables must be an instance of LanguageModelGatewayEnvironmentVariables"
            )

        self.dcr_manager: DcrManager = dcr_manager
        if self.dcr_manager is None:
            raise ValueError("dcr_manager must not be None")

    async def check_tokens_are_valid_for_tools(
        self,
        *,
        auth_information: AuthInformation,
        headers: Dict[str, Any],
        model_config: ChatModelConfig,
    ) -> None:
        tools_using_authentication: List[AgentConfig] = (
            [a for a in model_config.get_agents() if a.auth == "jwt_token"]
            if model_config.get_agents() is not None
            else []
        )
        if not tools_using_authentication:
            logger.debug("No tools require authentication.")
            return

        auth_headers = [
            headers.get(key) for key in headers if key.lower() == "authorization"
        ]
        auth_header: str | None = auth_headers[0] if auth_headers else None
        for tool_using_authentication in tools_using_authentication:
            await self.check_tokens_are_valid_for_tool(
                auth_header=auth_header,
                auth_information=auth_information,
                authentication_config=tool_using_authentication,
            )

    async def _ensure_oauth_provider_registered(
        self,
        *,
        auth_provider: str,
        oauth: McpOAuthConfig,
    ) -> AuthConfig:
        """Dynamically register an auth provider from .mcp.json oauth config.

        Uses ``DcrManager`` for credential resolution (pre-registered or DCR)
        and ``AuthManager.register_dynamic_provider()`` for OAuth client
        registration with proper PKCE config.
        """
        existing: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=auth_provider
            )
        )
        if existing is not None:
            return existing

        # Resolve client_id — either from config or via DCR
        client_id = oauth.client_id
        client_secret = oauth.client_secret

        dcr_result = await self.dcr_manager.resolve_dcr_credentials(
            auth_provider=auth_provider,
            registration_url=oauth.registration_url,
            client_id=oauth.client_id,
            client_name=(
                oauth.client_metadata.client_name if oauth.client_metadata else None
            ),
            client_uri=(
                oauth.client_metadata.client_uri if oauth.client_metadata else None
            ),
            logo_uri=(
                oauth.client_metadata.logo_uri if oauth.client_metadata else None
            ),
            contacts=(
                oauth.client_metadata.contacts if oauth.client_metadata else None
            ),
        )

        if dcr_result is not None:
            client_id = dcr_result.client_id
            client_secret = dcr_result.client_secret

        if not client_id:
            raise ValueError(
                f"Could not resolve client_id for auth_provider '{auth_provider}'"
            )

        auth_config = AuthConfig(
            auth_provider=auth_provider,
            friendly_name=auth_provider,
            audience=client_id,
            client_id=client_id,
            client_secret=client_secret,
            well_known_uri=oauth.auth_server_metadata_url,
            scope=oauth.scope_string,
            authorization_endpoint=oauth.authorization_url,
            token_endpoint=oauth.token_url,
            use_pkce=oauth.use_pkce,
            pkce_method=oauth.pkce_method,
            registration_url=oauth.registration_url,
        )

        # Register in AuthConfigReader for lookup
        configs = self.auth_config_reader.get_auth_configs_for_all_auth_providers()
        configs.append(auth_config)

        # Register OAuth client via clean API
        await self.auth_manager.register_dynamic_provider(auth_config=auth_config)

        logger.info(
            "Registered OAuth provider '%s' (client_id=%s, pkce=%s/%s)",
            auth_provider,
            client_id,
            oauth.use_pkce,
            oauth.pkce_method,
        )

        return auth_config

    async def check_tokens_are_valid_for_tool(
        self,
        *,
        auth_header: str | None,
        auth_information: AuthInformation,
        authentication_config: AuthenticationConfig,
    ) -> TokenCacheItem | None:
        tool_auth_providers: list[str] | None = authentication_config.auth_providers
        if (
            authentication_config.auth_providers is None
            or len(authentication_config.auth_providers) == 0
        ):
            logger.debug(
                f"Tool {authentication_config.name} doesn't have auth providers."
            )
            return None
        if not auth_information.redirect_uri:
            logger.debug("AuthInformation doesn't have redirect_uri.")
            return None

        if not auth_information.subject:
            logger.debug("AuthInformation doesn't have subject.")
            return None

        tool_first_auth_provider: str | None = (
            tool_auth_providers[0] if tool_auth_providers is not None else None
        )
        auth_config: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=tool_first_auth_provider
            )
            if tool_first_auth_provider is not None
            else None
        )
        # If not found in static config, try to register from .mcp.json oauth
        if (
            auth_config is None
            and tool_first_auth_provider
            and authentication_config.oauth
        ):
            auth_config = await self._ensure_oauth_provider_registered(
                auth_provider=tool_first_auth_provider,
                oauth=authentication_config.oauth,
            )
        if auth_config is None:
            raise ValueError(
                f"AuthConfig not found for auth provider {tool_first_auth_provider}"
                f" used by tool {authentication_config.name}."
            )
        if not auth_information.subject:
            logger.error(
                f"AuthInformation is missing subject for tool '{authentication_config.name}'."
            )
            raise ValueError(
                "AuthInformation must have subject to authenticate for tools."
                + (f"{auth_information}" if logger.isEnabledFor(logging.DEBUG) else "")
            )
        if not tool_first_auth_provider:
            raise ValueError("Tool using authentication must have an auth provider.")
        tool_auth_provider: str = tool_first_auth_provider
        tool_client_id: str | None = (
            auth_config.client_id if auth_config is not None else None
        )
        if not tool_client_id:
            raise ValueError("Tool using authentication must have a client ID.")

        # This is for logging in with Okta
        authorization_url: (
            str | None
        ) = await self.auth_manager.create_authorization_url(
            auth_provider=tool_auth_provider,
            redirect_uri=auth_information.redirect_uri,
            url=authentication_config.url,
            referring_email=auth_information.email,
            referring_subject=auth_information.subject,
        )

        app_login_uri = self.environment_variables.app_login_uri
        app_login_url_with_parameters: str | None = None
        if app_login_uri:
            parsed_login_uri = urlparse(app_login_uri)
            existing_query_params = dict(
                parse_qsl(parsed_login_uri.query, keep_blank_values=True)
            )
            login_query_params: dict[str, str | None] = {
                "auth_provider": tool_auth_provider,
                "referring_email": auth_information.email,
                "referring_subject": auth_information.subject,
            }
            # create state
            sanitized_login_query_params = {
                "state": (AuthHelper.encode_state(content=login_query_params)),
            }
            merged_query_params = {
                **existing_query_params,
                **sanitized_login_query_params,
            }
            app_login_url_with_parameters = cast(  # type: ignore[redundant-cast]
                str,
                urlunparse(
                    parsed_login_uri._replace(query=urlencode(merged_query_params))
                ),
            )

        app_token_save_uri = self.environment_variables.app_token_save_uri
        app_token_save_uri_with_parameters: str | None = None
        if app_token_save_uri:
            parsed_token_save_uri = urlparse(app_token_save_uri)
            existing_query_params = dict(
                parse_qsl(parsed_token_save_uri.query, keep_blank_values=True)
            )
            token_save_query_params: dict[str, str | None] = {
                "auth_provider": tool_auth_provider,
                "referring_email": auth_information.email,
                "referring_subject": auth_information.subject,
            }
            sanitized_token_save_query_params = {
                "state": (AuthHelper.encode_state(content=token_save_query_params)),
            }
            merged_query_params = {
                **existing_query_params,
                **sanitized_token_save_query_params,
            }
            app_token_save_uri_with_parameters = cast(  # type: ignore[redundant-cast]
                str,
                urlunparse(
                    parsed_token_save_uri._replace(query=urlencode(merged_query_params))
                ),
            )

        error_message: str = (
            f"\nFollowing tools require authentication: {authentication_config.name}."
            + f"\nClick here to [Login to {auth_config.friendly_name}]({authorization_url})."
        )
        if app_login_url_with_parameters:
            error_message += f"\nClick here to [Login to b.well App]({app_login_url_with_parameters})."
        if app_token_save_uri_with_parameters:
            error_message += (
                f"\nClick here to [Paste Token]({app_token_save_uri_with_parameters})."
            )
        return await self.tool_auth_manager.get_token_for_tool_async(
            auth_header=auth_header,
            error_message=error_message,
            tool_config=authentication_config,
        )
