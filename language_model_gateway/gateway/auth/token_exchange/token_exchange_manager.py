import logging
from datetime import datetime, UTC
from typing import List

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

logger = logging.getLogger(__name__)


class TokenExchangeManager:
    """
    Manages the token exchange process.
    """

    def __init__(
        self, *, environment_variables: EnvironmentVariables, token_reader: TokenReader
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

    async def get_token_for_auth_provider_async(
        self, *, audience: str, email: str
    ) -> TokenCacheItem | None:
        """
        Get the token for the OIDC provider.

        This method retrieves the token from the cache or MongoDB based on the email and tool name.
        It returns a dictionary containing the token information.
        Returns:
            dict[str, Any]: A dictionary containing the token information.
        """

        # see if the token is in the cache
        token: TokenCacheItem | None = await self.token_repository.find_by_fields(
            collection_name=self.token_collection_name,
            model_class=TokenCacheItem,
            fields={
                "email": email,
                "audience": audience,
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

    async def get_valid_token_cache_item_for_audiences_async(
        self, *, audiences: List[str], email: str
    ) -> TokenCacheItem | None:
        """
        Check if a valid token exists for the given OIDC provider and email.

        Args:
            audiences (List[str]): The OIDC audiences to check.
            email (str): The email associated with the token.

        Returns:
            bool: True if a valid token exists, False otherwise.
        """
        # check if the bearer token has audience same as the auth provider name
        assert audiences is not None
        if not email:
            return None

        found_cache_item: (
            TokenCacheItem | None
        ) = await self.get_token_cache_item_for_audiences_async(
            audiences=audiences, email=email
        )
        return (
            found_cache_item
            if found_cache_item and found_cache_item.is_valid_id_token()
            else None
        )

    async def get_token_cache_item_for_audiences_async(
        self, *, audiences: List[str], email: str
    ) -> TokenCacheItem | None:
        """
        Check if a valid token exists for the given OIDC provider and email.
        If no valid token is found then it will return the last found token.

        Args:
            audiences (List[str]): The OIDC audiences to check.
            email (str): The email associated with the token.

        Returns:
            bool: True if a valid token exists, False otherwise.
        """
        # check if the bearer token has audience same as the auth provider name
        assert audiences is not None
        if not email:
            return None

        found_cache_item: TokenCacheItem | None = None
        for audience in audiences:
            token: TokenCacheItem | None = await self.get_token_for_auth_provider_async(
                audience=audience, email=email
            )
            if token:
                logger.debug(
                    f"Found token for audience {audience} and email {email}: {token.model_dump_json()}"
                )
                # we really care about the id token
                if token.is_valid_id_token():
                    logger.debug(
                        f"Found valid token for audience {audience} and email {email}"
                    )
                    return token
                else:
                    logger.info(
                        f"Token found is not valid for audience {audience} and email {email}: {token.model_dump_json() if token else 'None'}"
                    )
                    found_cache_item = token

        return found_cache_item

    async def get_token_for_tool_async(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_name: str,
        tool_auth_audiences: List[str] | None,
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
            tool_auth_audiences (List[str] | None): The list of audiences for the tool.
        Returns:
            Token | None: The token item if the token is valid, otherwise raises an exception.
        """
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
                if (
                    not tool_auth_audiences or token_audience in tool_auth_audiences
                ):  # token is valid
                    logger.debug(f"Token is valid for tool {tool_name}.")
                    return TokenCacheItem.create(
                        token=token_item,
                    )
                else:
                    # see if we have a token for this audience and email in the cache
                    email: (
                        str | None
                    ) = await self.token_reader.get_subject_from_token_async(token)
                    assert email, "Token must contain a subject (email or sub) claim."
                    token_for_tool: (
                        TokenCacheItem | None
                    ) = await self.get_token_cache_item_for_audiences_async(
                        audiences=tool_auth_audiences,
                        email=email,
                    )
                    if token_for_tool:
                        if token_for_tool.is_valid_id_token():
                            logger.debug(f"Found Token in cache for tool {tool_name}.")
                            return token_for_tool
                        else:
                            raise AuthorizationTokenCacheItemExpiredException(
                                message=f"Your token has expired for tool {tool_name}."
                                + error_message,
                                token_cache_item=token_for_tool,
                            )
                    else:
                        raise AuthorizationTokenCacheItemNotFoundException(
                            message="Token provided in Authorization header has wrong audience:"
                            + f"\nFound: {token_audience}, Expected: {','.join(tool_auth_audiences)}."
                            + "\nCould not find a cached token for the tool."
                            + error_message,
                            tool_auth_audiences=tool_auth_audiences,
                        )
            except AuthorizationNeededException:
                # just re-raise the exception with the original message
                raise
            except Exception as e:
                logger.error(f"Error verifying token for tool {tool_name}: {e}")
                logger.exception(e, stack_info=True)
                raise AuthorizationNeededException(
                    message="Invalid or expired token provided in Authorization header."
                    + error_message,
                ) from e

    async def save_token_async(
        self,
        *,
        token_cache_item: TokenCacheItem,
    ) -> TokenCacheItem:
        """
        Save the token to the database.

        This method saves the token to the MongoDB database. If the token already exists,
        it updates the existing token item. If it does not exist, it creates a new token
        item and inserts it into the database.

        Args:
            token_cache_item: TokenCacheItem to store in the database.
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
            item.refreshed = None
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
