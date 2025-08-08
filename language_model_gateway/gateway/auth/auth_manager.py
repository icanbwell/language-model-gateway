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
from language_model_gateway.gateway.auth.models.Token import Token
from language_model_gateway.gateway.auth.mongo.mongo_repository import (
    AsyncMongoRepository,
)

logger = logging.getLogger(__name__)


class AuthManager:
    def __init__(self) -> None:
        oauth_cache_type = os.getenv("OAUTH_CACHE", "memory")
        self.cache: OAuthCache = (
            OAuthMemoryCache() if oauth_cache_type == "memory" else OAuthMongoCache()
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
        self, *, redirect_uri: str, tool_name: str, request: Request
    ) -> str:
        """
        Create the authorization URL for the OIDC provider.
        """
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state_content = {
            "tool_name": tool_name,
        }
        # convert state_content to a string
        state: str = AuthHelper.encode_state(state_content)

        rv: Dict[str, Any] = await client.create_authorization_url(
            redirect_uri=redirect_uri, state=state
        )
        await client.save_authorize_data(request, redirect_uri=redirect_uri, **rv)
        return cast(str, rv["url"])

    async def read_callback_response(self, *, request: Request) -> dict[str, Any]:
        client: StarletteOAuth2App = self.oauth.create_client(self.auth_provider_name)
        state: str | None = request.query_params.get("state")
        code: str | None = request.query_params.get("code")
        assert state is not None, "State must be provided in the callback"
        state_decoded: Dict[str, Any] = AuthHelper.decode_state(state)
        logger.info(f"State decoded: {state_decoded}")
        logger.info(f"Code received: {code}")
        token = await client.authorize_access_token(request)
        access_token = token["access_token"]
        id_token = token["id_token"]
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
        mongo_repository: AsyncMongoRepository[Token] = AsyncMongoRepository(
            connection_string=connection_string,
            database_name=database_name,
        )
        collection_name = os.getenv("MONGO_DB_TOKEN_COLLECTION_NAME")
        assert collection_name is not None, (
            "MONGO_DB_TOKEN_COLLECTION_NAME environment variable must be set"
        )
        stored_token_item: Token | None = await mongo_repository.find_by_fields(
            collection_name=collection_name,
            model_class=Token,
            fields={
                "email": email,
                "name": state_decoded["tool_name"],
            },
        )
        if stored_token_item is None:
            # Create a new token item if it does not exist
            stored_token_item = Token(
                _id=ObjectId(),
                name=state_decoded["tool_name"],
                email=email,
                url=None,
                access_token=access_token,
                id_token=id_token,
                expires_at=None,
                created_at=None,
            )
            await mongo_repository.save(
                collection_name=collection_name,
                model=stored_token_item,
            )
        else:
            # Update the existing token item
            stored_token_item.access_token = access_token
            stored_token_item.id_token = id_token
            await mongo_repository.save(
                collection_name=collection_name,
                model=stored_token_item,
            )
        return content
