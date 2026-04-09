import logging
import os

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.models.token import Token

logger = logging.getLogger(__name__)


class KeyCloakHelper:
    @staticmethod
    async def get_keycloak_access_token_async(
        username: str, password: str
    ) -> Token | None:
        """
        Fetch an OAuth2 access token using Resource Owner Password Credentials grant.
        Args:
            username (str): The user's username.
            password (str): The user's password.
        Returns:
            Token | None: The parsed token, or None if login fails.
        """
        oauth_client_id = os.getenv("AUTH_CLIENT_ID_CLIENT1")
        assert oauth_client_id is not None
        oauth_client_secret = os.getenv("AUTH_CLIENT_SECRET_CLIENT1")
        assert oauth_client_secret is not None
        openid_provider_url = os.getenv("AUTH_WELL_KNOWN_URI_CLIENT1")
        assert openid_provider_url is not None

        auth_config = AuthConfig(
            auth_provider="client1",
            friendly_name="client1",
            audience=oauth_client_id,
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            well_known_uri=openid_provider_url,
            scope="openid",
        )

        access_token: str = (
            await AuthManager.login_and_get_token_with_username_password_async(
                auth_config=auth_config,
                username=username,
                password=password,
            )
        )
        return Token.create_from_token(token=access_token)
