import logging
from typing import Dict, Any

from authlib.integrations.starlette_client import StarletteOAuth2App
from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_expired_exception import (
    AuthorizationTokenCacheItemExpiredException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class ToolAuthManager:
    def __init__(
        self,
        *,
        token_exchange_manager: TokenExchangeManager,
        auth_config_reader: AuthConfigReader,
        auth_manager: AuthManager,
    ) -> None:
        self.token_exchange_manager: TokenExchangeManager = token_exchange_manager
        if self.token_exchange_manager is None:
            raise ValueError("token_exchange_manager must not be None")
        if not isinstance(self.token_exchange_manager, TokenExchangeManager):
            raise TypeError(
                "token_exchange_manager must be an instance of TokenExchangeManager"
            )

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )

        self.auth_manager: AuthManager = auth_manager
        if self.auth_manager is None:
            raise ValueError("auth_manager must not be None")
        if not isinstance(self.auth_manager, AuthManager):
            raise TypeError("auth_manager must be an instance of AuthManager")

    async def get_token_for_tool_async(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_config: AgentConfig,
    ) -> TokenCacheItem | None:
        """
        Get the token for the specified tool.

        This method retrieves the token for the specified tool from the token exchange manager.
        If the token is not found, it raises an AuthorizationNeededException with the provided error message.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            error_message (str): The error message to display if authorization is needed.
            tool_config (AgentConfig): The tool configuration.
        Returns:
            str | None: The token for the specified tool, or None if not found.
        Raises:
            AuthorizationNeededException: If the token is not found and authorization is needed.
        """
        logger.debug(
            f"Getting token for tool '{tool_config.name}' "
            f"with auth providers {tool_config.auth_providers} "
            f"with auth_header: {auth_header}"
        )

        if not tool_config.auth_providers:
            raise ValueError(
                f"Tool '{tool_config.name}' has no auth_providers configured."
            )

        try:
            token_cache_item: (
                TokenCacheItem | None
            ) = await self.token_exchange_manager.get_token_for_tool_async(
                auth_header=auth_header,
                error_message=error_message,
                tool_config=tool_config,
            )
            logger.debug(f"AuthManager Token retrieved: {token_cache_item}")
            if token_cache_item is None:
                logger.debug(
                    f"No token found for audience '{tool_config.auth_providers}'."
                )
                return None

            # if id_token is valid, return it
            if token_cache_item.is_valid_id_token():
                logger.debug(
                    f"Token for tool '{tool_config.name}' is valid:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}"
                )
                return token_cache_item

            if token_cache_item.audience and token_cache_item.is_expired():
                logger.debug(
                    f"Token for tool '{tool_config.name}' is expired, refreshing..."
                )
                return await self.refresh_tokens_with_oidc(
                    audience=token_cache_item.audience,
                    token_cache_item=token_cache_item,
                )
            else:
                logger.debug(
                    f"Token for tool '{tool_config.name}' is not expired:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}."
                )
                return token_cache_item
        except AuthorizationTokenCacheItemExpiredException as e:
            # if the token is expired, try to refresh it
            logger.debug(
                f"Token for tool '{tool_config.name}' is expired, trying to refresh: {e.message}"
            )
            if (
                e.token_cache_item
                and e.token_cache_item.audience
                and e.token_cache_item.is_expired()
                and e.token_cache_item.refresh_token
            ):
                refreshed_token = await self.refresh_tokens_with_oidc(
                    audience=e.token_cache_item.audience,
                    token_cache_item=e.token_cache_item,
                )
                return refreshed_token
            else:
                raise e

    async def refresh_tokens_with_oidc(
        self, audience: str, token_cache_item: TokenCacheItem
    ) -> TokenCacheItem | None:
        """
        Given a refresh token, call the OIDC token endpoint using authlib and decode the returned access and ID tokens using joserfc.
        Args:
            audience (str): The audience/client to use for OIDC.
            token_cache_item (TokenCacheItem): The token item to use for OIDC.
        Returns:
            dict: Contains 'access_token', 'id_token', and their decoded claims.
        Raises:
            Exception: If token refresh fails or tokens are invalid.
        """
        logger.debug(
            f"Refreshing token for audience '{audience}' with token_cache_item:\n{token_cache_item.model_dump_json()}"
        )
        client: StarletteOAuth2App = await self.auth_manager.create_oauth_client(
            name=token_cache_item.auth_provider
        )
        if client is None:
            raise ValueError(f"OIDC client for audience '{audience}' not found.")

        if (
            not token_cache_item.refresh_token
            or not token_cache_item.is_valid_refresh_token()
        ):
            logger.debug(
                f"Refresh token for audience '{audience}' not found or is not valid:"
                + f"\n{token_cache_item.refresh_token.model_dump_json() if token_cache_item.refresh_token else 'No Refresh token found.'}."
            )
            return None

        # Prepare token refresh request
        token_response: Dict[str, Any] = await client.fetch_access_token(  # type: ignore[no-untyped-call]
            grant_type="refresh_token",
            refresh_token=token_cache_item.refresh_token.token,
        )
        logger.debug(f"Token response received: {token_response}")
        return await self.token_exchange_manager.create_and_cache_token_async(
            token_response=token_response, token_cache_item=token_cache_item
        )
