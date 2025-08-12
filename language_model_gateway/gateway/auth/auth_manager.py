import logging
import os
from typing import Any, Dict, cast

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from bson import ObjectId
from fastapi import Request

from language_model_gateway.gateway.auth.auth_helper import AuthHelper
from language_model_gateway.gateway.auth.cache.oauth_cache import OAuthCache
from language_model_gateway.gateway.auth.cache.oauth_memory_cache import (
    OAuthMemoryCache,
)
from language_model_gateway.gateway.auth.cache.oauth_mongo_cache import OAuthMongoCache
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

logger = logging.getLogger(__name__)


class AuthManager:
    """
    AuthManager is responsible for managing authentication using OIDC PKCE.

    It initializes the OAuth client with the necessary configuration and provides methods
    to create authorization URLs and handle callback responses.
    """

    def __init__(self, *, environment_variables: EnvironmentVariables) -> None:
        """
        Initialize the AuthManager with the necessary configuration for OIDC PKCE.
        It sets up the OAuth cache, reads environment variables for the OIDC provider,
        and configures the OAuth client.
        The environment variables required are:
        - AUTH_PROVIDER_NAME: The name of the OIDC provider.
        - AUTH_WELL_KNOWN_URI: The well-known URL of the OIDC provider
        - AUTH_CLIENT_ID: The client ID for the OIDC application.
        - AUTH_CLIENT_SECRET: The client secret for the OIDC application.
        - AUTH_REDIRECT_URI: The redirect URI for the OIDC application.
        - MONGO_URL: The connection string for the MongoDB database.
        - MONGO_DB_NAME: The name of the MongoDB database.
        - MONGO_DB_TOKEN_COLLECTION_NAME: The name of the MongoDB collection for tokens.
        It also initializes the OAuth cache based on the OAUTH_CACHE environment variable,
        which can be set to "memory" for in-memory caching or "mongo" for MongoDB caching.
        If the OAUTH_CACHE environment variable is not set, it defaults to "memory".
        """
        self.environment_variables: EnvironmentVariables = environment_variables
        assert self.environment_variables is not None
        assert isinstance(self.environment_variables, EnvironmentVariables), (
            "environment_variables must be an instance of EnvironmentVariables"
        )

        oauth_cache_type = environment_variables.oauth_cache
        self.cache: OAuthCache = (
            OAuthMemoryCache()
            if oauth_cache_type == "memory"
            else OAuthMongoCache(environment_variables=environment_variables)
        )

        logger.info(
            f"Initializing AuthManager with cache type {type(self.cache)} cache id: {self.cache.id}"
        )
        # OIDC PKCE setup
        self.auth_provider_name = os.getenv("AUTH_PROVIDER_NAME")
        self.well_known_url = os.getenv("AUTH_WELL_KNOWN_URI")
        self.client_id = os.getenv("AUTH_CLIENT_ID")
        self.client_secret = os.getenv("AUTH_CLIENT_SECRET")
        self.redirect_uri = os.getenv("AUTH_REDIRECT_URI")
        # session_secret = os.getenv("AUTH_SESSION_SECRET")
        assert self.auth_provider_name is not None, (
            "AUTH_PROVIDER_NAME environment variable must be set"
        )
        assert self.well_known_url is not None, (
            "AUTH_WELL_KNOWN_URI environment variable must be set"
        )
        assert self.client_id is not None, (
            "AUTH_CLIENT_ID environment variable must be set"
        )
        assert self.client_secret is not None, (
            "AUTH_CLIENT_SECRET environment variable must be set"
        )
        assert self.redirect_uri is not None, (
            "AUTH_REDIRECT_URI environment variable must be set"
        )
        # assert session_secret is not None, (
        #     "AUTH_SESSION_SECRET environment variable must be set"
        # )

        # https://docs.authlib.org/en/latest/client/frameworks.html#frameworks-clients
        self.oauth: OAuth = OAuth(cache=self.cache)
        self.oauth.register(
            name=self.auth_provider_name,
            client_id=self.client_id,
            client_secret=self.client_secret,
            server_metadata_url=self.well_known_url,
            client_kwargs={"scope": "openid email", "code_challenge_method": "S256"},
        )

    async def create_authorization_url(
        self, *, redirect_uri: str, audience: str
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
        Returns:
            str: The authorization URL to redirect the user to for authentication.
        """
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state_content = {
            "audience": audience,
        }
        # convert state_content to a string
        state: str = AuthHelper.encode_state(state_content)

        rv: Dict[str, Any] = await client.create_authorization_url(
            redirect_uri=redirect_uri, state=state
        )
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
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state: str | None = request.query_params.get("state")
        code: str | None = request.query_params.get("code")
        assert state is not None, "State must be provided in the callback"
        state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
        logger.info(f"State decoded: {state_decoded}")
        logger.info(f"Code received: {code}")
        token = await client.authorize_access_token(request)
        access_token = token.get("access_token")
        id_token = token.get("id_token")
        assert access_token is not None, (
            "access_token was not found in the token response"
        )
        email: str = token.get("userinfo", {}).get("email")
        logger.info(f"Email received: {email}")
        # auth_token_exchange_client_id = os.getenv("AUTH_TOKEN_EXCHANGE_CLIENT_ID")
        # assert auth_token_exchange_client_id is not None, (
        #     "AUTH_TOKEN_EXCHANGE_CLIENT_ID environment variable must be set"
        # )
        content = {
            "token": token,
            "state": state_decoded,
            "code": code,
            "email": email,
        }

        connection_string = os.getenv("MONGO_URL")
        assert connection_string is not None, (
            "MONGO_URL environment variable must be set"
        )
        database_name = os.getenv("MONGO_DB_NAME")
        assert database_name is not None, (
            "MONGO_DB_NAME environment variable must be set"
        )
        mongo_repository: AsyncBaseRepository[TokenItem] = (
            RepositoryFactory.get_repository(
                repository_type=self.environment_variables.oauth_cache,
                environment_variables=self.environment_variables,
            )
        )
        collection_name = os.getenv("MONGO_DB_TOKEN_COLLECTION_NAME")
        assert collection_name is not None, (
            "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
        )
        audience = state_decoded["audience"]
        stored_token_item: TokenItem | None = await mongo_repository.find_by_fields(
            collection_name=collection_name,
            model_class=TokenItem,
            fields={
                "email": email,
                "name": audience,
            },
        )
        if stored_token_item is None:
            # Create a new token item if it does not exist
            stored_token_item = TokenItem(
                _id=ObjectId(),
                name=audience,
                email=email,
                url=None,
                access_token=access_token,
                id_token=id_token,
                expires_at=None,
                created_at=None,
            )
            await mongo_repository.insert(
                collection_name=collection_name,
                model=stored_token_item,
            )
        else:
            # Update the existing token item
            stored_token_item.access_token = access_token
            stored_token_item.id_token = id_token
            await mongo_repository.insert(
                collection_name=collection_name,
                model=stored_token_item,
            )
        return content
