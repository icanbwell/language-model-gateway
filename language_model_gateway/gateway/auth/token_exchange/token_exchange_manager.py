from language_model_gateway.gateway.auth.models.token_item import TokenItem
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)
from language_model_gateway.gateway.auth.repository.repository_factory import (
    RepositoryFactory,
)
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)


class TokenExchangeManager:
    """
    Manages the token exchange process.
    """

    def __init__(self, *, environment_variables: EnvironmentVariables) -> None:
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

    async def get_token_for_auth_provider(
        self, *, auth_provider_name: str, email: str
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
                "name": auth_provider_name,
            },
        )
        return token

    async def store_token(
        self, *, token: TokenItem, email: str, auth_provider_name: str
    ) -> None:
        """
        Store the token in the cache or MongoDB.

        This method stores the token in the cache or MongoDB based on the email and tool name.
        Args:
            token (Token): The token to store.
            email (str): The email associated with the token.
            auth_provider_name (str): The name of the OIDC provider.
        """
        await self.token_repository.insert_or_update(
            collection_name=self.token_collection_name,
            model_class=TokenItem,
            item=token,
            fields={
                "email": email,
                "name": auth_provider_name,
            },
        )

    async def has_valid_token_for_auth_provider(
        self, *, auth_provider_name: str, email: str, bearer_token: str
    ) -> bool:
        """
        Check if a valid token exists for the given OIDC provider and email.

        Args:
            auth_provider_name (str): The name of the OIDC provider.
            email (str): The email associated with the token.
            bearer_token (str): The bearer token to verify.

        Returns:
            bool: True if a valid token exists, False otherwise.
        """
        # check if the bearer token has audience same as the auth provider name
        if not bearer_token:
            return False
        if not auth_provider_name:
            return False
        if not email:
            return False
        # get the token for the auth provider and email
        # and check if it is valid
        if not bearer_token.startswith("Bearer "):
            return False
        # extract the token from the bearer token
        token_value = bearer_token[len("Bearer ") :]
        if not token_value:
            return False

        token: TokenItem | None = await self.get_token_for_auth_provider(
            auth_provider_name=auth_provider_name, email=email
        )
        return token is not None and token.is_valid()
