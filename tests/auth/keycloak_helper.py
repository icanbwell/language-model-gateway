import logging
import os

from language_model_gateway.gateway.auth.authenticator.oauth_authenticator import (
    OAuthAuthenticator,
)
from oidcauthlib.auth.models.token import Token

logger = logging.getLogger(__name__)


class KeyCloakHelper:
    @staticmethod
    def get_keycloak_access_token(username: str, password: str) -> Token | None:
        """
        Fetch an OAuth2 access token using Resource Owner Password Credentials grant.
        Args:
            username (str): The user's username.
            password (str): The user's password.
        Returns:
            dict: The token response.
        """
        oauth_client_id = os.getenv("AUTH_CLIENT_ID_CLIENT1")
        assert oauth_client_id is not None
        oauth_client_secret = os.getenv("AUTH_CLIENT_SECRET_CLIENT1")
        assert oauth_client_secret is not None
        openid_provider_url = os.getenv("AUTH_WELL_KNOWN_URI_CLIENT1")
        assert openid_provider_url is not None

        return OAuthAuthenticator.login_and_get_oauth_access_token(
            username=username,
            password=password,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            openid_provider_url=openid_provider_url,
        )
