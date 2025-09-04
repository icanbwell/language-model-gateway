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
        oauth_client_id = "bwell-client-id"
        # oauth_client_secret = os.getenv("oauth_client_secret", "bwell-secret")
        oauth_client_secret = "bwell-secret"
        openid_provider_url = os.getenv(
            "openid_provider_url",
            "http://keycloak:8080/realms/bwell-realm/.well-known/openid-configuration",
        )

        resp = requests.get(openid_provider_url, timeout=5)
        resp.raise_for_status()
        openid_config = resp.json()
        token_endpoint = openid_config["token_endpoint"]

        # https://docs.authlib.org/en/latest/client/oauth2.html
        client = OAuth2Session(
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            # scope="openid email offline_access",
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
