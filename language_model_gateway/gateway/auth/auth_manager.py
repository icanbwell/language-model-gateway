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
from language_model_gateway.gateway.utilities.logger.logging_transport import (
    LoggingTransport,
)

logger = logging.getLogger(__name__)


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
        assert self.environment_variables is not None
        assert isinstance(self.environment_variables, EnvironmentVariables), (
            "environment_variables must be an instance of EnvironmentVariables"
        )

        self.token_exchange_manager: TokenExchangeManager = token_exchange_manager
        assert self.token_exchange_manager is not None
        assert isinstance(self.token_exchange_manager, TokenExchangeManager)

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        assert self.auth_config_reader is not None
        assert isinstance(self.auth_config_reader, AuthConfigReader)

        self.token_reader: TokenReader = token_reader
        assert self.token_reader is not None
        assert isinstance(self.token_reader, TokenReader)

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
        assert self.redirect_uri is not None, (
            "AUTH_REDIRECT_URI environment variable must be set"
        )
        # https://docs.authlib.org/en/latest/client/frameworks.html#frameworks-clients
        self.oauth: OAuth = OAuth(cache=self.cache)
        # read AUTH_PROVIDERS comma separated list from the environment variable and register the OIDC provider for each provider
        auth_configs: List[AuthConfig] = (
            self.auth_config_reader.get_auth_configs_for_all_audiences()
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
        self, *, redirect_uri: str, audience: str, issuer: str, url: str | None
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
        Returns:
            str: The authorization URL to redirect the user to for authentication.
        """
        # default to first audience
        client: StarletteOAuth2App = self.oauth.create_client(audience)
        assert client is not None, f"Client for audience {audience} not found"
        state_content: Dict[str, str | None] = {
            "audience": audience,
            "issuer": issuer,
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
        assert state is not None, "State must be provided in the callback"
        state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
        logger.debug(f"State decoded: {state_decoded}")
        logger.debug(f"Code received: {code}")
        audience: str | None = state_decoded.get("audience")
        logger.debug(f"Audience retrieved: {audience}")
        issuer: str | None = state_decoded.get("issuer")
        assert issuer is not None, "Issuer must be provided in the callback"
        logger.debug(f"Issuer retrieved: {issuer}")
        url: str | None = state_decoded.get("url")
        logger.debug(f"URL retrieved: {url}")
        client: StarletteOAuth2App = self.oauth.create_client(audience)
        token = await client.authorize_access_token(request)
        access_token: str | None = token.get("access_token")
        id_token: str | None = token.get("id_token")
        refresh_token: str | None = token.get("refresh_token")
        assert access_token is not None, (
            "access_token was not found in the token response"
        )
        email: str = token.get("userinfo", {}).get("email")
        subject: str = token.get("userinfo", {}).get("sub")
        logger.debug(f"Email received: {email}")
        logger.debug(f"Subject received: {subject}")
        content = {
            "token": token,
            "state": state_decoded,
            "code": code,
            "subject": subject,
            "email": email,
            "issuer": issuer,
        }
        audience = state_decoded["audience"]

        token_cache_item: TokenCacheItem = TokenCacheItem(
            _id=ObjectId(),
            access_token=Token.create(token=access_token),
            id_token=Token.create(token=id_token),
            refresh_token=Token.create(token=refresh_token),
            email=email,
            subject=subject,
            issuer=issuer,
            audience=audience,
            referrer=url,
        )

        await self.token_exchange_manager.save_token_async(
            token_cache_item=token_cache_item, refreshed=False
        )

        if logger.isEnabledFor(logging.DEBUG):
            access_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=access_token.strip("\n"),
                    verify_signature=False,
                )
                if access_token
                else None
            )
            id_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=id_token.strip("\n"),
                    verify_signature=False,
                )
                if id_token
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

    async def get_token_for_tool_async(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_name: str,
        tool_auth_audiences: List[str] | None,
    ) -> TokenCacheItem | None:
        """
        Get the token for the specified tool.

        This method retrieves the token for the specified tool from the token exchange manager.
        If the token is not found, it raises an AuthorizationNeededException with the provided error message.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            error_message (str): The error message to display if authorization is needed.
            tool_name (str): The name of the tool for which the token is requested.
            tool_auth_audiences (List[str] | None): The list of audiences for which the tool requires authentication.
        Returns:
            str | None: The token for the specified tool, or None if not found.
        Raises:
            AuthorizationNeededException: If the token is not found and authorization is needed.
        """
        logger.debug(
            f"Getting token for tool '{tool_name}' with audiences {tool_auth_audiences} with auth_header: {auth_header}"
        )

        try:
            token_cache_item: (
                TokenCacheItem | None
            ) = await self.token_exchange_manager.get_token_for_tool_async(
                auth_header=auth_header,
                error_message=error_message,
                tool_name=tool_name,
                tool_auth_audiences=tool_auth_audiences,
            )
            logger.debug(f"AuthManager Token retrieved: {token_cache_item}")
            if token_cache_item is None:
                logger.debug(f"No token found for audience '{tool_auth_audiences}'.")
                return None

            # if id_token is valid, return it
            if token_cache_item.is_valid_id_token():
                logger.debug(
                    f"Token for tool '{tool_name}' is valid:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}"
                )
                return token_cache_item

            if token_cache_item.audience and token_cache_item.is_expired():
                return await self.refresh_tokens_with_oidc(
                    audience=token_cache_item.audience,
                    token_cache_item=token_cache_item,
                )
            else:
                logger.debug(
                    f"Token for tool '{tool_name}' is not expired:"
                    + f"\n{token_cache_item.id_token.model_dump_json() if token_cache_item.id_token else 'No ID token found.'}."
                )
        except AuthorizationTokenCacheItemExpiredException as e:
            # if the token is expired, try to refresh it
            if (
                e.token_cache_item
                and e.token_cache_item.audience
                and e.token_cache_item.is_expired()
            ):
                return await self.refresh_tokens_with_oidc(
                    audience=e.token_cache_item.audience,
                    token_cache_item=e.token_cache_item,
                )

        return None

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

        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")
        refresh_token = token_response.get("refresh_token")
        if not access_token or not id_token:
            raise Exception(
                "OIDC token refresh did not return access_token or id_token."
            )

        token_cache_item.access_token = Token.create(token=access_token)
        token_cache_item.id_token = Token.create(token=id_token)
        token_cache_item.refresh_token = Token.create(token=refresh_token)
        token_cache_item.refreshed = datetime.now(tz=UTC)

        new_token_item: TokenCacheItem = (
            await self.token_exchange_manager.save_token_async(
                token_cache_item=token_cache_item, refreshed=True
            )
        )
        return new_token_item
