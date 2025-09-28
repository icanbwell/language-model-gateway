import logging
from datetime import datetime, UTC
from typing import List

from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.exceptions.authorization_bearer_token_missing_exception import (
    AuthorizationBearerTokenMissingException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_expired_exception import (
    AuthorizationTokenCacheItemExpiredException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_token_cache_item_not_found_exception import (
    AuthorizationTokenCacheItemNotFoundException,
)
from language_model_gateway.gateway.auth.models.token import Token
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)
from language_model_gateway.gateway.auth.repository.repository_factory import (
    RepositoryFactory,
)
from language_model_gateway.gateway.auth.token_reader import TokenReader
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
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
        environment_variables: EnvironmentVariables,
        token_reader: TokenReader,
        auth_config_reader: AuthConfigReader,
    ) -> None:
        assert environment_variables is not None
        assert environment_variables.mongo_uri is not None
        assert environment_variables.mongo_db_name is not None
        self.token_repository: AsyncBaseRepository[TokenCacheItem] = (
            RepositoryFactory.get_repository(
                repository_type=environment_variables.oauth_cache,
                environment_variables=environment_variables,
            )
        )
        self.environment_variables: EnvironmentVariables = environment_variables
        assert self.token_repository is not None, (
            "TokenExchangeManager requires a token repository to be set up."
        )
        assert isinstance(environment_variables, EnvironmentVariables), (
            "TokenExchangeManager requires EnvironmentVariables instance."
        )
        assert environment_variables.mongo_db_token_collection_name is not None
        self.token_collection_name: str = (
            environment_variables.mongo_db_token_collection_name
        )
        assert self.token_collection_name is not None, (
            "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
        )

        self.token_reader: TokenReader = token_reader
        assert self.token_reader is not None, (
            "TokenExchangeManager requires a TokenReader instance."
        )
        assert isinstance(token_reader, TokenReader)

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        assert self.auth_config_reader is not None
        assert isinstance(self.auth_config_reader, AuthConfigReader)

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
                "auth_provider": auth_provider,
            },
        )
        return token

    async def store_token_async(
        self, *, token: TokenCacheItem, email: str, audience: str
    ) -> None:
        """
        Store the token in the cache or MongoDB.

        This method stores the token in the cache or MongoDB based on the email and tool name.
        Args:
            token (Token): The token to store.
            email (str): The email associated with the token.
            audience (str): The name of the OIDC provider.
        """
        await self.token_repository.insert_or_update(
            collection_name=self.token_collection_name,
            model_class=TokenCacheItem,
            item=token,
            keys={
                "email": email,
                "name": audience,
            },
        )

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
        # check if the bearer token has audience same as the auth provider name
        assert auth_providers is not None
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
                    f"Found token for auth_provider {auth_provider}, audience {audience} and referring_email {referring_email}: {token.model_dump_json()}"
                )
                # we really care about the id token
                if token.is_valid_id_token():
                    logger.debug(
                        f"Found valid token for auth_provider {auth_provider}, audience {audience} and referring_email {referring_email}"
                    )
                    return token
                else:
                    logger.info(
                        f"Token found is not valid for auth_provider {auth_provider}, audience {audience} and referring_email {referring_email}: {token.model_dump_json() if token else 'None'}"
                    )
                    found_cache_item = token

        logger.debug(
            f"Found token cache item for auth providers {auth_providers} referring_email {referring_email}: {found_cache_item}"
        )
        return found_cache_item

    async def get_token_for_tool_async(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_name: str,
        tool_auth_providers: List[str] | None,
    ) -> TokenCacheItem | None:
        """
        Get the token for the tool using the Authorization header.

        This method checks if the Authorization header is present and extracts the token.
        If the token is valid, it returns the token item. If the token is not valid
        or the Authorization header is missing, it raises an AuthorizationNeededException.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            error_message (str): The error message to include in the exception if the token is invalid
            tool_name (str): The name of the tool for which the token is being requested.
            tool_auth_providers (List[str] | None): The list of audiences for the tool.
        Returns:
            Token | None: The token item if the token is valid, otherwise raises an exception.
        """
        if tool_auth_providers is not None:
            # capitalize all auth providers to ensure case insensitive comparison
            tool_auth_providers = [ap.upper() for ap in tool_auth_providers]

        logger.debug(
            f"Getting token for tool {tool_name} with auth_providers {tool_auth_providers}."
        )
        if not auth_header:
            logger.debug(f"Authorization header is missing for tool {tool_name}.")
            raise AuthorizationBearerTokenMissingException(
                message="Authorization header is required for MCP tools with JWT authentication."
                + error_message,
            )
        else:  # auth_header is present
            token: str | None = self.token_reader.extract_token(auth_header)
            if not token:
                logger.debug(
                    f"No token found in Authorization header for tool {tool_name}."
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
                assert token_item is not None
                # get the audience from the token
                token_audience: str | List[str] | None = token_item.audience
                token_auth_provider: str | None = (
                    self.auth_config_reader.get_provider_for_audience(
                        audience=token_audience
                        if isinstance(token_audience, str)
                        else token_audience[0]
                    )
                    if token_audience
                    else "unknown"
                )
                if (
                    not tool_auth_providers
                    or token_auth_provider in tool_auth_providers
                ):  # token is valid
                    logger.debug(
                        f"Token is valid for tool {tool_name} with token_auth_provider {token_auth_provider}."
                    )

                    if not token_item.email:
                        raise ValueError("Token must have an email claim.")
                    if not token_item.subject:
                        raise ValueError("Token must have a subject claim.")

                    # now create a TokenCacheItem from the token to store in the db
                    return TokenCacheItem.create(
                        token=token_item,
                        auth_provider=token_auth_provider
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
                    assert email, "Token must contain a subject (email or sub) claim."

                    # now find token for this email and auth provider
                    token_for_tool: (
                        TokenCacheItem | None
                    ) = await self.get_token_cache_item_for_auth_providers_async(
                        auth_providers=tool_auth_providers,
                        referring_email=email,
                    )
                    if token_for_tool:
                        if token_for_tool.is_valid_id_token():
                            logger.debug(
                                f"Found Token in cache for tool {tool_name} for email {email} and auth_provider {token_auth_provider}."
                            )
                            return token_for_tool
                        else:
                            logger.debug(
                                f"Token has expired for tool {tool_name} for email {email} and auth_provider {token_auth_provider}."
                            )
                            raise AuthorizationTokenCacheItemExpiredException(
                                message=f"Your token has expired for tool {tool_name}."
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
                            + f"\nFound auth provider: {token_auth_provider} for audience {token_audience}"
                            + f", Expected auth provider: {','.join(tool_auth_providers)}."
                            + f"\nEmail (sub) in token: {email}."
                            + f"\nCould not find a cached token for the tool for auth_providers {','.join(tool_auth_providers)} and email {email}."
                            + error_message,
                            tool_auth_providers=tool_auth_providers,
                        )
            except AuthorizationNeededException:
                # just re-raise the exception with the original message
                raise
            except Exception as e:
                logger.exception(f"Error verifying token for tool {tool_name}: {e}")
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
        assert connection_string is not None, (
            "MONGO_URL environment variable must be set"
        )
        database_name = self.environment_variables.mongo_db_name
        assert database_name is not None, (
            "MONGO_DB_NAME environment variable must be set"
        )
        mongo_repository: AsyncBaseRepository[TokenCacheItem] = (
            RepositoryFactory.get_repository(
                repository_type=self.environment_variables.oauth_cache,
                environment_variables=self.environment_variables,
            )
        )
        collection_name = self.environment_variables.mongo_db_token_collection_name
        assert collection_name is not None, (
            "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
        )
        assert token_cache_item.issuer is not None, (
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
        await mongo_repository.insert_or_update(
            collection_name=collection_name,
            item=token_cache_item,
            keys={
                "email": token_cache_item.email,
                "audience": token_cache_item.audience,
                "issuer": token_cache_item.issuer,
            },
            model_class=TokenCacheItem,
            on_insert=on_insert,
            on_update=on_update,
        )

        return token_cache_item
