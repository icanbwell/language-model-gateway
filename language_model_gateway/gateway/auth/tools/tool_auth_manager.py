from datetime import datetime, UTC
import logging
from typing import Dict, Any

from authlib.integrations.starlette_client import StarletteOAuth2App
from bson import ObjectId
from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.models.token import Token

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

    def create_token_cache_item(
        self,
        *,
        code: str | None,
        issuer: str,
        state_decoded: dict[str, Any],
        token: Dict[str, Any],
        url: str | None,
    ) -> TokenCacheItem:
        access_token: str | None = token.get("access_token")
        access_token_item = Token.create_from_token(token=access_token)

        id_token: str | None = token.get("id_token")
        id_token_item = Token.create_from_token(token=id_token)

        refresh_token: str | None = token.get("refresh_token")
        refresh_token_item = Token.create_from_token(token=refresh_token)

        if access_token is None:
            raise ValueError("access_token was not found in the token response")

        email: str | None = (
            token.get("userinfo", {}).get("email")
            or (access_token_item.email if access_token_item else None)
            or (id_token_item.email if id_token_item else None)
        )
        subject: str | None = (
            token.get("userinfo", {}).get("sub")
            or (access_token_item.subject if access_token_item else None)
            or (id_token_item.subject if id_token_item else None)
        )

        if not email:
            raise ValueError("email must be provided in the token")
        if not subject:
            raise ValueError("subject must be provided in the token")

        logger.debug(f"Email received: {email}")
        logger.debug(f"Subject received: {subject}")
        referring_email = state_decoded.get("referring_email")
        referring_subject = state_decoded.get("referring_subject")
        # content = {
        #     "token": token,
        #     "state": state_decoded,
        #     "code": code,
        #     "subject": subject,
        #     "email": email,
        #     "issuer": issuer,
        #     "referring_email": referring_email,
        #     "referring_subject": referring_subject,
        # }
        audience = state_decoded["audience"]
        auth_provider: str | None = (
            self.auth_config_reader.get_provider_for_audience(audience=audience)
            if audience
            else "unknown"
        )

        if not referring_email:
            raise ValueError("referring_email must be provided in the state")
        if not referring_subject:
            raise ValueError("referring_subject must be provided in the state")

        token_cache_item: TokenCacheItem = TokenCacheItem(
            _id=ObjectId(),
            access_token=access_token_item,
            id_token=id_token_item,
            refresh_token=refresh_token_item,
            email=email,
            subject=subject,
            issuer=issuer,
            audience=audience,
            referrer=url,
            auth_provider=auth_provider if auth_provider else "unknown",
            created=datetime.now(UTC),
            referring_email=referring_email,
            referring_subject=referring_subject,
        )
        return token_cache_item

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
            f"Getting token for tool '{tool_config.name}' with auth providers {tool_config.auth_providers} with auth_header: {auth_header}"
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
        client: StarletteOAuth2App = self.auth_manager.oauth.create_client(audience)
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
        token_response: Dict[str, Any] = await client.fetch_access_token(
            grant_type="refresh_token",
            refresh_token=token_cache_item.refresh_token.token,
        )
        logger.debug(f"Token response received: {token_response}")
        return await self.create_and_cache_token_async(
            token_response=token_response, token_cache_item=token_cache_item
        )

    async def create_and_cache_token_async(
        self, *, token_response: dict[str, Any], token_cache_item: TokenCacheItem
    ) -> TokenCacheItem:
        """
        Create and cache a new token from the token response.
        Args:
            token_response (dict): The token response containing access_token, id_token, refresh_token, etc.
            token_cache_item (TokenCacheItem): The token cache item to update and save.
        Returns:
            TokenCacheItem: The updated and saved token cache item.
        Raises:
        """
        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")
        refresh_token = token_response.get("refresh_token")
        if not access_token or not id_token:
            raise Exception(
                "OIDC token refresh did not return access_token or id_token."
            )

        return await self.cache_token_async(
            access_token=access_token,
            id_token=id_token,
            refresh_token=refresh_token,
            token_cache_item=token_cache_item,
        )

    async def cache_token_async(
        self,
        *,
        access_token: str | None,
        id_token: str | None,
        refresh_token: str | None,
        token_cache_item: TokenCacheItem,
    ) -> TokenCacheItem:
        """
        Cache the provided tokens in the token cache item and save it using the token exchange manager.
        Args:
            access_token (str | None): The access token to cache.
            id_token (str | None): The ID token to cache.
            refresh_token (str | None): The refresh token to cache.
            token_cache_item (TokenCacheItem): The token cache item to update and save.
        Returns:
            TokenCacheItem: The updated and saved token cache item.
        """

        if token_cache_item is None:
            raise ValueError("token_cache_item must not be None")

        if not isinstance(token_cache_item, TokenCacheItem):
            raise TypeError(f"TokenCacheItem must be of type {TokenCacheItem.__name__}")

        token_cache_item.access_token = Token.create_from_token(token=access_token)
        token_cache_item.id_token = Token.create_from_token(token=id_token)
        token_cache_item.refresh_token = Token.create_from_token(token=refresh_token)
        token_cache_item.refreshed = datetime.now(tz=UTC)

        new_token_item: TokenCacheItem = (
            await self.token_exchange_manager.save_token_async(
                token_cache_item=token_cache_item, refreshed=True
            )
        )
        return new_token_item
