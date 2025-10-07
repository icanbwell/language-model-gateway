from datetime import datetime, UTC

import httpx
import logging
import os
import uuid
from typing import Any, Dict, cast, List

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from bson import ObjectId
from fastapi import Request

from language_model_gateway.gateway.auth.auth_helper import AuthHelper
from language_model_gateway.gateway.auth.cache.oauth_cache import OAuthCache
from language_model_gateway.gateway.auth.cache.oauth_memory_cache import (
    OAuthMemoryCache,
)
from language_model_gateway.gateway.auth.cache.oauth_mongo_cache import OAuthMongoCache
from language_model_gateway.gateway.auth.config.auth_config import AuthConfig
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_expired_exception import (
    AuthorizationTokenCacheItemExpiredException,
)
from language_model_gateway.gateway.auth.models.token import Token
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.auth.token_reader import TokenReader
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.logger.logging_transport import (
    LoggingTransport,
)

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class AuthManager:
    """
    AuthManager is responsible for managing authentication using OIDC PKCE.

    It initializes the OAuth client with the necessary configuration and provides methods
    to create authorization URLs and handle callback responses.
    """

    def __init__(
        self,
        *,
        environment_variables: EnvironmentVariables,
        token_exchange_manager: TokenExchangeManager,
        auth_config_reader: AuthConfigReader,
        token_reader: TokenReader,
    ) -> None:
        """
        Initialize the AuthManager with the necessary configuration for OIDC PKCE.
        It sets up the OAuth cache, reads environment variables for the OIDC provider,
        and configures the OAuth client.
        The environment variables required are:
        - MONGO_URL: The connection string for the MongoDB database.
        - MONGO_DB_NAME: The name of the MongoDB database.
        - MONGO_DB_TOKEN_COLLECTION_NAME: The name of the MongoDB collection for tokens.
        It also initializes the OAuth cache based on the OAUTH_CACHE environment variable,
        which can be set to "memory" for in-memory caching or "mongo" for MongoDB caching.
        If the OAUTH_CACHE environment variable is not set, it defaults to "memory".

        Args:
            environment_variables (EnvironmentVariables): The environment variables for the application.
            token_exchange_manager (TokenExchangeManager): The manager for handling token exchanges.
            auth_config_reader (AuthConfigReader): The reader for authentication configurations.
            token_reader (TokenReader): The reader for tokens.
        """
        self.environment_variables: EnvironmentVariables = environment_variables
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(self.environment_variables, EnvironmentVariables):
            raise TypeError(
                "environment_variables must be an instance of EnvironmentVariables"
            )

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

        self.token_reader: TokenReader = token_reader
        if self.token_reader is None:
            raise ValueError("token_reader must not be None")
        if not isinstance(self.token_reader, TokenReader):
            raise TypeError("token_reader must be an instance of TokenReader")

        oauth_cache_type = environment_variables.oauth_cache
        self.cache: OAuthCache = (
            OAuthMemoryCache()
            if oauth_cache_type == "memory"
            else OAuthMongoCache(environment_variables=environment_variables)
        )

        logger.debug(
            f"Initializing AuthManager with cache type {type(self.cache)} cache id: {self.cache.id}"
        )
        # OIDC PKCE setup
        self.redirect_uri = os.getenv("AUTH_REDIRECT_URI")
        if self.redirect_uri is None:
            raise ValueError("AUTH_REDIRECT_URI environment variable must be set")
        # https://docs.authlib.org/en/latest/client/frameworks.html#frameworks-clients
        self.oauth: OAuth = OAuth(cache=self.cache)
        # read AUTH_PROVIDERS comma separated list from the environment variable and register the OIDC provider for each provider
        auth_configs: List[AuthConfig] = (
            self.auth_config_reader.get_auth_configs_for_all_auth_providers()
        )

        auth_config: AuthConfig
        for auth_config in auth_configs:
            self.oauth.register(
                name=auth_config.audience,
                client_id=auth_config.client_id,
                client_secret=auth_config.client_secret,
                server_metadata_url=auth_config.well_known_uri,
                client_kwargs={
                    "scope": "openid email",
                    "code_challenge_method": "S256",
                    "transport": LoggingTransport(httpx.AsyncHTTPTransport()),
                },
            )

    async def create_authorization_url(
        self,
        *,
        redirect_uri: str,
        audience: str,
        issuer: str,
        url: str | None,
        referring_email: str,
        referring_subject: str,
    ) -> str:
        """
        Create the authorization URL for the OIDC provider.

        This method generates the authorization URL with the necessary parameters,
        including the redirect URI and state. The state is encoded to include the tool name,
        which is used to identify the tool that initiated the authentication process.
        Args:
            redirect_uri (str): The redirect URI to which the OIDC provider will send the user
                after authentication.
            audience (str): The audience we need to get a token for.
            issuer (str): The issuer of the OIDC provider, used to validate the token.
            url (str): The URL of the tool that has requested this.
            referring_email (str): The email of the user who initiated the request.
            referring_subject (str): The subject of the user who initiated the request.
        Returns:
            str: The authorization URL to redirect the user to for authentication.
        """
        # default to first audience
        client: StarletteOAuth2App = self.oauth.create_client(audience)
        if client is None:
            raise ValueError(f"Client for audience {audience} not found")
        state_content: Dict[str, str | None] = {
            "audience": audience,
            "auth_provider": self.auth_config_reader.get_provider_for_audience(
                audience=audience
            ),
            "issuer": issuer,
            "referring_email": referring_email,
            "referring_subject": referring_subject,
            "url": url,  # the URL of the tool that has requested this
            # include a unique request ID so we don't get cache for another request
            # This will create a unique state for each request
            # the callback will use this state to find the correct token
            "request_id": uuid.uuid4().hex,
        }
        # convert state_content to a string
        state: str = AuthHelper.encode_state(state_content)

        logger.debug(
            f"Creating authorization URL for audience {audience} with state {state_content} and encoded state {state}"
        )

        rv: Dict[str, Any] = await client.create_authorization_url(
            redirect_uri=redirect_uri, state=state
        )
        logger.debug(f"Authorization URL created: {rv}")
        # request is only needed if we are using the session to store the state
        await client.save_authorize_data(request=None, redirect_uri=redirect_uri, **rv)
        return cast(str, rv["url"])

    async def read_callback_response(self, *, request: Request) -> dict[str, Any]:
        """
        Handle the callback response from the OIDC provider after the user has authenticated.

        This method retrieves the authorization code and state from the request,
        decodes the state to get the tool name, and exchanges the authorization code for an access
        token and ID token. It then stores the tokens in a MongoDB collection if they do
        not already exist, or updates the existing token if it does.
        Args:
            request (Request): The FastAPI request object containing the callback data.
        Returns:
            dict[str, Any]: A dictionary containing the token information, state, code, and email.
        """
        state: str | None = request.query_params.get("state")
        code: str | None = request.query_params.get("code")
        if state is None:
            raise ValueError("State must be provided in the callback")
        state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
        logger.debug(f"State decoded: {state_decoded}")
        logger.debug(f"Code received: {code}")
        audience: str | None = state_decoded.get("audience")
        logger.debug(f"Audience retrieved: {audience}")
        issuer: str | None = state_decoded.get("issuer")
        if issuer is None:
            raise ValueError("Issuer must be provided in the callback")
        logger.debug(f"Issuer retrieved: {issuer}")
        url: str | None = state_decoded.get("url")
        logger.debug(f"URL retrieved: {url}")
        client: StarletteOAuth2App = self.oauth.create_client(audience)
        token = await client.authorize_access_token(request)

        token_cache_item: TokenCacheItem = self.create_token_cache_item(
            code=code, issuer=issuer, state_decoded=state_decoded, token=token, url=url
        )

        await self.token_exchange_manager.save_token_async(
            token_cache_item=token_cache_item, refreshed=False
        )

        content: Dict[str, Any] = token_cache_item.model_dump()

        if logger.isEnabledFor(logging.DEBUG):
            access_token: str | None = (
                token_cache_item.access_token.token
                if token_cache_item.access_token
                else None
            )
            access_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=access_token.strip("\n"),
                    verify_signature=False,
                )
                if access_token
                else None
            )
            id_token: str | None = (
                token_cache_item.id_token.token if token_cache_item.id_token else None
            )
            id_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=id_token.strip("\n"),
                    verify_signature=False,
                )
                if id_token
                else None
            )
            refresh_token: str | None = (
                token_cache_item.refresh_token.token
                if token_cache_item.refresh_token
                else None
            )
            refresh_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=refresh_token.strip("\n"),
                    verify_signature=False,
                )
                if refresh_token
                else None
            )
            content["access_token_decoded"] = access_token_decoded
            content["id_token_decoded"] = id_token_decoded
            content["refresh_token_decoded"] = refresh_token_decoded

        return content

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
            token.get("userinfo", {}).get("email") or access_token_item.email
            if access_token_item
            else None or id_token_item.email
            if id_token_item
            else None
        )
        subject: str | None = (
            token.get("userinfo", {}).get("sub") or access_token_item.subject
            if access_token_item
            else None or id_token_item.subject
            if id_token_item
            else None
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
        tool_name: str,
        tool_auth_providers: List[str] | None,
    ) -> TokenCacheItem | None:
        """
        Get the token for the specified tool.

        This method retrieves the token for the specified tool from the token exchange manager.
        If the token is not found, it raises an AuthorizationNeededException with the provided error message.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            error_message (str): The error message to display if authorization is needed.
            tool_name (str): The name of the tool for which the token is requested.
            tool_auth_providers (List[str] | None): The list of audiences for which the tool requires authentication.
        Returns:
            str | None: The token for the specified tool, or None if not found.
        Raises:
            AuthorizationNeededException: If the token is not found and authorization is needed.
        """
        logger.debug(
            f"Getting token for tool '{tool_name}' with auth providers {tool_auth_providers} with auth_header: {auth_header}"
        )

        try:
            token_cache_item: (
                TokenCacheItem | None
            ) = await self.token_exchange_manager.get_token_for_tool_async(
                auth_header=auth_header,
                error_message=error_message,
                tool_name=tool_name,
                tool_auth_providers=tool_auth_providers,
            )
            logger.debug(f"AuthManager Token retrieved: {token_cache_item}")
            if token_cache_item is None:
                logger.debug(f"No token found for audience '{tool_auth_providers}'.")
                return None

            # if id_token is valid, return it
            if token_cache_item.is_valid_id_token():
                logger.debug(
                    f"Token for tool '{tool_name}' is valid:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}"
                )
                return token_cache_item

            if token_cache_item.audience and token_cache_item.is_expired():
                logger.debug(f"Token for tool '{tool_name}' is expired, refreshing...")
                return await self.refresh_tokens_with_oidc(
                    audience=token_cache_item.audience,
                    token_cache_item=token_cache_item,
                )
            else:
                logger.debug(
                    f"Token for tool '{tool_name}' is not expired:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}."
                )
                return token_cache_item
        except AuthorizationTokenCacheItemExpiredException as e:
            # if the token is expired, try to refresh it
            logger.debug(
                f"Token for tool '{tool_name}' is expired, trying to refresh: {e.message}"
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
        client: StarletteOAuth2App = self.oauth.create_client(audience)
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

        assert token_cache_item is not None, "token_cache_item must not be None"
        assert isinstance(token_cache_item, TokenCacheItem), (
            "token_cache_item must be a TokenCacheItem"
        )

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

    async def login_and_get_access_token_with_password_async(
        self,
        audience: str,
        username: str,
        password: str,
    ) -> TokenCacheItem:
        """
        Obtain an access token using Resource Owner Password Credentials (ROPC) grant.
        Args:
            audience (str): The audience/client to use for OIDC.
            username (str): The username of the resource owner.
            password (str): The password of the resource owner.
        Returns:
            dict[str, Any]: The token response containing access_token, id_token, refresh_token, etc.
        Raises:
            ValueError: If the OIDC client is not found or token response is invalid.
        """
        assert username, "username must not be None"
        assert password, "password must not be None"
        assert audience, "audience must not be None"
        logger.debug(
            f"Getting access token for audience '{audience}' using username/password grant."
        )
        client: StarletteOAuth2App = self.oauth.create_client(audience)
        if client is None:
            raise ValueError(f"OIDC client for audience '{audience}' not found.")
        token_response: dict[str, Any] = await client.fetch_access_token(
            grant_type="password",
            username=username,
            password=password,
        )
        logger.debug(f"Token response received: {token_response}")
        token_cache_item: TokenCacheItem = self.create_token_cache_item(
            code=None,
            issuer=client.server_metadata.get("issuer"),
            state_decoded={
                "audience": audience,
                "auth_provider": self.auth_config_reader.get_provider_for_audience(
                    audience=audience
                ),
                "referring_email": username,
                "referring_subject": username,
                "url": client.server_metadata.get("url"),
                "request_id": uuid.uuid4().hex,
            },
            token=token_response,
            url=client.server_metadata.get("url"),
        )
        return await self.create_and_cache_token_async(
            token_response=token_response, token_cache_item=token_cache_item
        )
