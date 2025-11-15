import logging
from typing import cast

import requests
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749 import OAuth2Token
from oidcauthlib.auth.models.token import Token

logger = logging.getLogger(__name__)


class OAuthAuthenticator:
    """
    Helper class for OAuth2 authentication.

    """

    @staticmethod
    def login_and_get_oauth_access_token(
        *,
        username: str,
        password: str,
        oauth_client_id: str,
        oauth_client_secret: str,
        openid_provider_url: str,
    ) -> Token | None:
        """
        Fetch an OAuth2 access token using Resource Owner Password Credentials grant.
        Args:
            username (str): The user's username.
            password (str): The user's password.
            oauth_client_id (str): The OAuth client ID.
            oauth_client_secret (str): The OAuth client secret.
            openid_provider_url (str): The OpenID provider well-known URL.
        Returns:
            dict: The token response.
        """
        if oauth_client_id is None:
            raise Exception("oauth_client_id must not be None")
        if oauth_client_secret is None:
            raise Exception("oauth_client_secret must not be None")
        if openid_provider_url is None:
            raise Exception("openid_provider_url must not be None")

        resp = requests.get(openid_provider_url, timeout=5)
        resp.raise_for_status()
        openid_config = resp.json()
        token_endpoint = openid_config["token_endpoint"]

        # https://docs.authlib.org/en/latest/client/oauth2.html
        client = OAuth2Session(
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            scope="openid",
        )

        try:
            token: dict[str, str] | OAuth2Token = client.fetch_token(
                url=token_endpoint,
                username=username,
                password=password,
                grant_type="password",
            )
        except Exception as e:
            logger.exception(f"Error fetching access token: {e}")
            raise
        return Token.create_from_token(token=cast(str, token.get("access_token")))
