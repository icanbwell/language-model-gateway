import logging
from datetime import datetime, UTC
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
            keys={
                "email": email,
                "name": audience,
            },
        )

    async def get_valid_token_for_audiences_async(
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
            # we really care about the id token
            if token and token.is_valid_id_token():
                return token

        return None

    async def get_token_for_tool_async(
        self,
        *,
        auth_header: str | None,
        error_message: str,
        tool_name: str,
        tool_auth_audiences: List[str] | None,
    ) -> TokenItem | None:
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
                token_item: (
                    TokenItem | None
                ) = await self.token_reader.verify_token_async(token=token)
                # get the audience from the token
                token_audience: (
                    str | None
                ) = await self.token_reader.get_audience_from_token_async(token=token)
                if (
                    not tool_auth_audiences or token_audience in tool_auth_audiences
                ):  # token is valid
                    logger.debug(f"Token is valid for tool {tool_name}.")
                    return token_item
                else:
                    # see if we have a token for this audience and email in the cache
                    email: (
                        str | None
                    ) = await self.token_reader.get_subject_from_token_async(token)
                    assert email, "Token must contain a subject (email or sub) claim."
                    token_for_tool: (
                        TokenItem | None
                    ) = await self.get_valid_token_for_audiences_async(
                        audiences=tool_auth_audiences,
                        email=email,
                    )
                    if token_for_tool:
                        logger.debug(f"Found Token in cache for tool {tool_name}.")
                        return token_for_tool
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
        subject: str,
        id_token: str | None,
        refresh_token: str | None,
        issuer: str | None,
        audience: str,
        url: str | None,
    ) -> None:
        """
        Save the token to the database.

        This method saves the token to the MongoDB database. If the token already exists,
        it updates the existing token item. If it does not exist, it creates a new token
        item and inserts it into the database.

        Args:
            access_token (str | None): The access token to store.
            email (str): The email associated with the token.
            subject (str): The subject of the token, typically the user ID or unique identifier.
            id_token (str | None): The ID token to store.
            refresh_token (str | None): The refresh token to store.
            issuer (str | None): The issuer of the token.
            audience (str): The audience for which the token is valid.
            url (str | None): The URL associated with the token.
        """
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
        assert access_token or id_token, (
            "Either id_token or access_token must be provided to store the token"
        )
        access_token_expires: datetime | None = (
            await self.token_reader.get_expires_from_token_async(token=access_token)
            if access_token
            else None
        )
        id_token_expires: datetime | None = (
            await self.token_reader.get_expires_from_token_async(token=id_token)
            if id_token
            else None
        )
        refresh_token_expires: datetime | None = (
            await self.token_reader.get_expires_from_token_async(token=refresh_token)
            if refresh_token
            else None
        )
        access_token_issued: datetime | None = (
            await self.token_reader.get_issued_from_token_async(token=access_token)
            if access_token
            else None
        )
        id_token_issued: datetime | None = (
            await self.token_reader.get_issued_from_token_async(token=id_token)
            if id_token
            else None
        )
        refresh_token_issued: datetime | None = (
            await self.token_reader.get_issued_from_token_async(token=refresh_token)
            if refresh_token
            else None
        )
        now: datetime = datetime.now(UTC)

        # Create a new token item if it does not exist
        if stored_token_item is None:
            stored_token_item = TokenItem(
                _id=ObjectId(),
                created=now,
                updated=None,
                issuer=issuer,
                audience=audience,
                email=email,
                subject=subject,
                url=url,
                access_token=access_token,
                id_token=id_token,
                refresh_token=refresh_token,
                access_token_expires=access_token_expires
                if access_token_expires
                else None,
                id_token_expires=id_token_expires,
                refresh_token_expires=refresh_token_expires,
                access_token_issued=access_token_issued,
                id_token_issued=id_token_issued,
                refresh_token_issued=refresh_token_issued,
                refreshed=None,
            )
        else:
            # Update the existing token item
            stored_token_item.updated = now
            stored_token_item.access_token = access_token
            stored_token_item.id_token = id_token
            stored_token_item.refresh_token = refresh_token
            stored_token_item.access_token_expires = access_token_expires
            stored_token_item.id_token_expires = id_token_expires
            stored_token_item.refresh_token_expires = refresh_token_expires
            stored_token_item.access_token_issued = access_token_issued
            stored_token_item.id_token_issued = id_token_issued
            stored_token_item.refresh_token_issued = refresh_token_issued
            stored_token_item.refreshed = (
                None  # since we are storing a new token, we set refreshed to None
            )

        # now insert or update the token item in the database
        await mongo_repository.insert_or_update(
            collection_name=collection_name,
            item=stored_token_item,
            keys={
                "email": email,
                "audience": audience,
                "issuer": issuer,
            },
            model_class=TokenItem,
        )
