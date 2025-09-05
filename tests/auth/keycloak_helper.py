import logging
import os
from typing import Dict, Any

from authlib.oauth2.rfc6749 import OAuth2Token

import requests
from authlib.integrations.requests_client import OAuth2Session

logger = logging.getLogger(__name__)


class KeyCloakHelper:
    @staticmethod
    def get_keycloak_access_token(username: str, password: str) -> Dict[str, Any]:
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
        return token if isinstance(token, dict) else token["access_token"]
