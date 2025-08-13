import logging
from datetime import datetime
from typing import List

from bson import ObjectId

from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.token_item import TokenItem
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
        self.token_repository: AsyncBaseRepository[TokenItem] = (
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
    ) -> TokenItem | None:
        """
        Get the token for the OIDC provider.

        This method retrieves the token from the cache or MongoDB based on the email and tool name.
        It returns a dictionary containing the token information.
        Returns:
            dict[str, Any]: A dictionary containing the token information.
        """

        # see if the token is in the cache
        token: TokenItem | None = await self.token_repository.find_by_fields(
            collection_name=self.token_collection_name,
            model_class=TokenItem,
            fields={
                "email": email,
                "audience": audience,
            },
        )
        return token

    async def store_token_async(
        self, *, token: TokenItem, email: str, audience: str
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
            model_class=TokenItem,
            item=token,
            fields={
                "email": email,
                "name": audience,
            },
        )

    async def get_valid_token_for_auth_provider_async(
        self, *, audiences: List[str], email: str
    ) -> TokenItem | None:
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

        for audience in audiences:
            token: TokenItem | None = await self.get_token_for_auth_provider_async(
                audience=audience, email=email
            )
            if token and token.is_valid():
                return token

        return None

    async def get_token_for_tool(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_name: str,
        tool_auth_audiences: List[str] | None,
    ) -> str | None:
        if not auth_header:
            logger.debug(f"Authorization header is missing for tool {tool_name}.")
            raise AuthorizationNeededException(
                "Authorization header is required for MCP tools with JWT authentication."
                + error_message
            )
        else:  # auth_header is present
            token: str | None = self.token_reader.extract_token(auth_header)
            if not token:
                logger.debug(
                    f"No token found in Authorization header for tool {tool_name}."
                )
                raise AuthorizationNeededException(
                    "Invalid Authorization header format. Expected 'Bearer <token>'"
                    + error_message
                )
            try:
                # verify the token
                await self.token_reader.verify_token_async(token=token)
                # get the audience from the token
                token_audience: (
                    str | None
                ) = await self.token_reader.get_audience_from_token_async(token=token)
                if (
                    not tool_auth_audiences or token_audience in tool_auth_audiences
                ):  # token is valid
                    logger.debug(f"Token is valid for tool {tool_name}.")
                    return token
                else:
                    # see if we have a token for this audience and email in the cache
                    email: (
                        str | None
                    ) = await self.token_reader.get_subject_from_token_async(token)
                    assert email, "Token must contain a subject (email or sub) claim."
                    token_for_tool: (
                        TokenItem | None
                    ) = await self.get_valid_token_for_auth_provider_async(
                        audiences=tool_auth_audiences,
                        email=email,
                    )
                    if token_for_tool:
                        logger.debug(f"Found Token in cache for tool {tool_name}.")
                        return (
                            token_for_tool.id_token
                            if token_for_tool.id_token
                            else token_for_tool.access_token
                        )
                    else:
                        logger.debug(
                            f"Token audience found: {token_audience} for tool {tool_name}."
                        )
                        raise AuthorizationNeededException(
                            "Token provided in Authorization header has wrong audience:"
                            + f"\nFound: {token_audience}, Expected: {','.join(tool_auth_audiences)}."
                            + "\nCould not find a cached token for the tool."
                            + error_message
                        )
            except AuthorizationNeededException:
                # just re-raise the exception with the original message
                raise
            except Exception as e:
                logger.error(f"Error verifying token for tool {tool_name}: {e}")
                logger.exception(e, stack_info=True)
                raise AuthorizationNeededException(
                    "Invalid or expired token provided in Authorization header."
                    + error_message
                ) from e

    async def save_token_async(
        self,
        *,
        access_token: str | None,
        email: str,
        id_token: str | None,
        issuer: str | None,
        audience: str,
        url: str | None,
    ) -> None:
        connection_string = self.environment_variables.mongo_uri
        assert connection_string is not None, (
            "MONGO_URL environment variable must be set"
        )
        database_name = self.environment_variables.mongo_db_name
        assert database_name is not None, (
            "MONGO_DB_NAME environment variable must be set"
        )
        mongo_repository: AsyncBaseRepository[TokenItem] = (
            RepositoryFactory.get_repository(
                repository_type=self.environment_variables.oauth_cache,
                environment_variables=self.environment_variables,
            )
        )
        collection_name = self.environment_variables.mongo_db_token_collection_name
        assert collection_name is not None, (
            "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
        )
        assert issuer is not None, (
            "Issuer must be provided in the state for storing the token"
        )
        stored_token_item: TokenItem | None = await mongo_repository.find_by_fields(
            collection_name=collection_name,
            model_class=TokenItem,
            fields={
                "email": email,
                "name": audience,
                "issuer": issuer,
            },
        )
        valid_token: str | None = id_token or access_token
        assert valid_token is not None, (
            "Either id_token or access_token must be provided to store the token"
        )
        expires_at: (
            datetime | None
        ) = await self.token_reader.get_expiration_from_token_async(token=valid_token)
        created_at: (
            datetime | None
        ) = await self.token_reader.get_created_at_from_token_async(token=valid_token)
        if stored_token_item is None:
            # Create a new token item if it does not exist
            stored_token_item = TokenItem(
                _id=ObjectId(),
                issuer=issuer,
                audience=audience,
                email=email,
                url=url,
                access_token=access_token,
                id_token=id_token,
                expires_at=expires_at.isoformat() if expires_at else None,
                created_at=created_at.isoformat() if created_at else None,
            )
        else:
            # Update the existing token item
            stored_token_item.access_token = access_token
            stored_token_item.id_token = id_token
            stored_token_item.expires_at = (
                expires_at.isoformat() if expires_at else None
            )
            stored_token_item.created_at = (
                created_at.isoformat() if created_at else None
            )

        # now insert or update the token item in the database
        await mongo_repository.insert_or_update(
            collection_name=collection_name,
            item=stored_token_item,
            fields={
                "email": email,
                "audience": audience,
                "issuer": issuer,
            },
            model_class=TokenItem,
        )
