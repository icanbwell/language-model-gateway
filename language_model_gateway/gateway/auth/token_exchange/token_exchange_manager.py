import logging
from datetime import datetime, UTC
from typing import List, Any

from bson import ObjectId
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.exceptions.authorization_bearer_token_missing_exception import (
    AuthorizationBearerTokenMissingException,
)
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from oidcauthlib.auth.repository.base_repository import AsyncBaseRepository
from oidcauthlib.auth.repository.repository_factory import RepositoryFactory

from language_model_gateway.configs.config_schema import AgentConfig
from oidcauthlib.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_expired_exception import (
    AuthorizationTokenCacheItemExpiredException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_not_found_exception import (
    AuthorizationTokenCacheItemNotFoundException,
)
from oidcauthlib.auth.models.token import Token

from oidcauthlib.auth.token_reader import TokenReader

from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["TOKEN_EXCHANGE"])


class TokenExchangeManager:
    """
    Manages the token exchange process.
    """

    def __init__(
        self,
        *,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        token_reader: TokenReader,
        auth_config_reader: AuthConfigReader,
    ) -> None:
        if environment_variables is None:
            raise ValueError(
                "TokenExchangeManager requires environment_variables to be provided."
            )
        if environment_variables.mongo_uri is None:
            raise ValueError("MONGO_URL environment variable must be set.")
        if environment_variables.mongo_db_name is None:
            raise ValueError("MONGO_DB_NAME environment variable must be set.")
        self.token_repository: AsyncBaseRepository[TokenCacheItem] = (
            RepositoryFactory.get_repository(
                repository_type=environment_variables.oauth_cache,
                environment_variables=environment_variables,
            )
        )
        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )
        if self.token_repository is None:
            raise ValueError(
                "TokenExchangeManager requires a token repository to be set up."
            )
        if not isinstance(
            environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "TokenExchangeManager requires EnvironmentVariables instance."
            )
        if environment_variables.mongo_db_token_collection_name is None:
            raise ValueError(
                "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set."
            )
        self.token_collection_name: str = (
            environment_variables.mongo_db_token_collection_name
        )
        if self.token_collection_name is None:
            raise ValueError(
                "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set."
            )

        self.token_reader: TokenReader = token_reader
        if self.token_reader is None:
            raise ValueError("TokenExchangeManager requires a TokenReader instance.")
        if not isinstance(token_reader, TokenReader):
            raise TypeError("token_reader must be a TokenReader instance.")

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError(
                "TokenExchangeManager requires an AuthConfigReader instance."
            )
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError("auth_config_reader must be an AuthConfigReader instance.")

    async def get_token_for_auth_provider_and_referring_email(
        self, *, auth_provider: str, referring_email: str
    ) -> TokenCacheItem | None:
        """
        Get the token for the OIDC provider.

        This method retrieves the token from the cache or MongoDB based on the email and tool name.
        It returns a dictionary containing the token information.

        Args:
            auth_provider (str): The name of the OIDC provider.
            referring_email (str): The email associated with the token.
        Returns:
            dict[str, Any]: A dictionary containing the token information.
        """

        # see if the token is in the cache
        token: TokenCacheItem | None = await self.token_repository.find_by_fields(
            collection_name=self.token_collection_name,
            model_class=TokenCacheItem,
            fields={
                "referring_email": referring_email,
                "auth_provider": auth_provider.lower(),
            },
        )
        return token

    async def get_token_cache_item_for_auth_providers_async(
        self, *, auth_providers: List[str], referring_email: str
    ) -> TokenCacheItem | None:
        """
        Check if a valid token exists for the given OIDC provider and email.
        If no valid token is found then it will return the last found token.

        Args:
            auth_providers (List[str]): The OIDC providers to check.
            referring_email (str): The email associated with the token.

        Returns:
            bool: True if a valid token exists, False otherwise.
        """
        if auth_providers is None:
            raise ValueError("auth_providers must be provided.")
        # check if the bearer token has audience same as the auth provider name
        if not referring_email:
            return None

        found_cache_item: TokenCacheItem | None = None
        for auth_provider in auth_providers:
            audience: str = self.auth_config_reader.get_audience_for_provider(
                auth_provider=auth_provider
            )
            token: (
                TokenCacheItem | None
            ) = await self.get_token_for_auth_provider_and_referring_email(
                auth_provider=auth_provider, referring_email=referring_email
            )
            if token:
                logger.debug(
                    f"Found token for auth_provider {auth_provider}, audience {audience} "
                    f"and referring_email {referring_email}: {token.model_dump_json()}"
                )
                # we really care about the id token
                if token.is_valid_id_token():
                    logger.debug(
                        f"Found valid token for auth_provider {auth_provider}, audience {audience} and referring_email {referring_email}"
                    )
                    return token
                else:
                    logger.info(
                        f"Token found is not valid for auth_provider {auth_provider}, audience {audience} and referring_email {referring_email}: {token.model_dump_json() if token is not None else 'None'}"
                    )
                    found_cache_item = token

        logger.debug(
            f"Found token cache item for auth providers {auth_providers} referring_email {referring_email}: {found_cache_item}"
        )
        return found_cache_item

    async def get_token_for_tool_async(
        self, *, auth_header: str | None, error_message: str, tool_config: AgentConfig
    ) -> TokenCacheItem | None:
        """
        Get the token for the tool using the Authorization header.

        This method checks if the Authorization header is present and extracts the token.
        If the token is valid, it returns the token item. If the token is not valid
        or the Authorization header is missing, it raises an AuthorizationNeededException.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            error_message (str): The error message to include in the exception if the token is invalid
            tool_config (AgentConfig): The tool configuration to use.
        Returns:
            Token | None: The token item if the token is valid, otherwise raises an exception.
        """
        if tool_config is None:
            raise Exception("tool_config must not be None")
        if not isinstance(tool_config, AgentConfig):
            raise Exception("tool_config must be an instance of AgentConfig")

        tool_auth_providers: List[str] = (
            [ap.lower() for ap in tool_config.auth_providers]
            if tool_config.auth_providers
            else []
        )

        logger.debug(
            f"Getting token for tool {tool_config.name} with auth_providers {tool_auth_providers}."
        )
        if not auth_header:
            logger.debug(
                f"Authorization header is missing for tool {tool_config.name}."
            )
            raise AuthorizationBearerTokenMissingException(
                message="Authorization header is required for MCP tools with JWT authentication."
                + error_message,
            )
        else:  # auth_header is present
            token: str | None = self.token_reader.extract_token(
                authorization_header=auth_header
            )
            if not token:
                logger.debug(
                    f"No token found in Authorization header for tool {tool_config.name}."
                )
                raise AuthorizationBearerTokenMissingException(
                    message="Invalid Authorization header format. Expected 'Bearer <token>'"
                    + error_message,
                )
            try:
                # verify the token
                token_item: Token | None = await self.token_reader.verify_token_async(
                    token=token
                )
                if token_item is None:
                    raise ValueError("Token verification failed: token_item is None.")
                # get the audience from the token
                client_id: str | None = token_item.client_id
                token_auth_provider: str | None = (
                    self.auth_config_reader.get_provider_for_client_id(
                        client_id=client_id
                    )
                    if client_id
                    else "unknown"
                )
                if (
                    not tool_auth_providers
                    or not token_auth_provider
                    or token_auth_provider.lower()
                    in [c.lower() for c in tool_auth_providers]
                ):  # token is valid
                    logger.debug(
                        f"Token is valid for tool {tool_config.name} with token_auth_provider {token_auth_provider}."
                    )

                    if not token_item.email:
                        raise ValueError("Token must have an email claim.")
                    if not token_item.subject:
                        raise ValueError("Token must have a subject claim.")

                    # now create a TokenCacheItem from the token to store in the db
                    return TokenCacheItem.create(
                        token=token_item,
                        auth_provider=token_auth_provider.lower()
                        if token_auth_provider
                        else "unknown",
                        referring_email=token_item.email,
                        referring_subject=token_item.subject,
                    )
                else:
                    # see if we have a token for this audience and email in the cache
                    email: (
                        str | None
                    ) = await self.token_reader.get_subject_from_token_async(
                        token=token
                    )
                    if not email:
                        raise ValueError(
                            "Token must contain a subject (email or sub) claim."
                        )

                    # now find token for this email and auth provider
                    token_for_tool: (
                        TokenCacheItem | None
                    ) = await self.get_token_cache_item_for_auth_providers_async(
                        auth_providers=tool_auth_providers,
                        referring_email=email,
                    )
                    if token_for_tool:
                        if token_for_tool.is_valid_access_token():
                            logger.debug(
                                f"Found Token in cache for tool {tool_config.name} for email {email} and auth_provider {token_auth_provider}."
                            )
                            return token_for_tool
                        else:
                            logger.debug(
                                f"Token has expired for tool {tool_config.name} for email {email} and auth_provider {token_auth_provider}."
                            )
                            raise AuthorizationTokenCacheItemExpiredException(
                                message=f"Your token has expired for tool {tool_config.name}."
                                + error_message,
                                token_cache_item=token_for_tool,
                            )
                    else:
                        logger.debug(
                            "Token provided in Authorization header has wrong token provider:"
                            + f"\nFound: {token_auth_provider}, Expected: {','.join(tool_auth_providers)}."
                        )
                        raise AuthorizationTokenCacheItemNotFoundException(
                            message="Token provided in Authorization header has wrong auth provider:"
                            + f"\nFound auth provider: {token_auth_provider} for client_id :{client_id}."
                            + f", Expected auth provider: {','.join(tool_auth_providers)}."
                            + f"\nEmail (sub) in token: {email}."
                            + f"\nCould not find a cached token for the tool for auth_providers {','.join(tool_auth_providers)} and email {email}."
                            + error_message,
                            tool_auth_providers=tool_auth_providers,
                        )
            except AuthorizationNeededException as e:
                # if tool does not need auth, then we can ignore the exception
                if tool_config.auth_optional:
                    return None
                # just re-raise the exception with the original message
                logger.exception(e, stack_info=True)
                raise
            except Exception as e:
                logger.exception(
                    f"Error verifying token for tool {tool_config.name}: {e}"
                )
                raise AuthorizationNeededException(
                    message="Invalid or expired token provided in Authorization header."
                    + (
                        f"\n{type(e).__name__}: {e}\n{token}\n"
                        if logger.isEnabledFor(logging.DEBUG)
                        else ""
                    )
                    + error_message,
                ) from e

    async def save_token_async(
        self, *, token_cache_item: TokenCacheItem, refreshed: bool
    ) -> TokenCacheItem:
        """
        Save the token to the database.

        This method saves the token to the MongoDB database. If the token already exists,
        it updates the existing token item. If it does not exist, it creates a new token
        item and inserts it into the database.

        Args:
            token_cache_item: TokenCacheItem to store in the database.
            refreshed: bool indicating if the token was refreshed.
        """
        connection_string = self.environment_variables.mongo_uri
        if connection_string is None:
            raise ValueError("MONGO_URL environment variable must be set")
        database_name = self.environment_variables.mongo_db_name
        if database_name is None:
            raise ValueError("MONGO_DB_NAME environment variable must be set")
        collection_name = self.environment_variables.mongo_db_token_collection_name
        if collection_name is None:
            raise ValueError(
                "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
            )
        if token_cache_item.issuer is None:
            raise ValueError(
                "Issuer must be provided in the state for storing the token"
            )

        now = datetime.now(UTC)

        def on_insert(item: TokenCacheItem) -> TokenCacheItem:
            item.created = now
            return item

        def on_update(item: TokenCacheItem) -> TokenCacheItem:
            # update the token item with the new token
            item.updated = now
            item.refreshed = now if refreshed else None
            return item

        # now insert or update the token item in the database
        await self.token_repository.insert_or_update(
            collection_name=collection_name,
            item=token_cache_item,
            keys={
                "email": token_cache_item.email,
                "auth_provider": token_cache_item.auth_provider,
            },
            model_class=TokenCacheItem,
            on_insert=on_insert,
            on_update=on_update,
        )

        return token_cache_item

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

        new_token_item: TokenCacheItem = await self.save_token_async(
            token_cache_item=token_cache_item, refreshed=True
        )
        return new_token_item

    # noinspection PyMethodMayBeStatic
    def create_token_cache_item(
        self,
        *,
        code: str | None,
        auth_config: AuthConfig,
        state_decoded: dict[str, Any],
        token: dict[str, Any],
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
            issuer=auth_config.issuer,
            audience=auth_config.audience,
            referrer=url,
            auth_provider=auth_config.auth_provider.lower(),
            client_id=auth_config.client_id,
            created=datetime.now(UTC),
            referring_email=referring_email,
            referring_subject=referring_subject,
        )
        return token_cache_item
