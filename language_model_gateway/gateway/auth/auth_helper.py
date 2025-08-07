import base64
import json
import logging
from typing import Dict, Any, cast
import os
import time

import httpx
import joserfc
from joserfc.jwt import encode
from joserfc.jwk import import_key

logger = logging.getLogger(__name__)


class AuthHelper:
    @staticmethod
    async def exchange_token(
        url: str,
        client_id: str,
        access_token: str,
        scope: str,
        client_secret: str | None = None,
        private_key: str | None = None,
        actor_token: str | None = None,
    ) -> Dict[str, str]:
        """
        Exchange an access token using Okta's token exchange endpoint.

        Args:
            url: The URL of the Okta token exchange endpoint
            client_id: The service application's client ID
            access_token: The original access token from Authorization Code with PKCE flow
            scope: Optional scope for the new token
            client_secret: The service application's client secret (optional)
            private_key: The private key in PEM format (optional)
            actor_token: The actor token for token exchange (optional)

        Returns:
            A dictionary containing the token exchange response
        """
        # Prepare headers and form data
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        form_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "subject_token": access_token,
            "scope": scope,
            # "audience": audience
        }
        if actor_token:
            form_data["actor_token"] = actor_token
            form_data["actor_token_type"] = (
                "urn:ietf:params:oauth:token-type:access_token"
            )
        if private_key:
            # Use private_key_jwt authentication
            now = int(time.time())
            payload = {
                "iss": client_id,
                "sub": client_id,
                "aud": url,
                "iat": now,
                "exp": now + 300,
                "jti": os.urandom(16).hex(),
            }
            jwk = import_key(private_key, "RSA")
            client_assertion = encode({"alg": "RS256"}, payload, jwk)
            form_data["client_assertion_type"] = (
                "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            )
            form_data["client_assertion"] = client_assertion
            form_data["client_id"] = client_id
        elif client_secret:
            # Use Basic Auth
            credentials = f"{client_id}:{client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode(
                "utf-8"
            )
            headers["Authorization"] = f"Basic {encoded_credentials}"
        else:
            raise ValueError("Either client_secret or private_key must be provided.")

        try:
            async with httpx.AsyncClient() as client:
                logger.info(
                    f"Exchanging token at {url} with headers: {headers} and form data: {form_data}"
                )
                response = await client.post(url, headers=headers, data=form_data)
                logger.info(f"Response from token exchange: {response.text}")
                response.raise_for_status()  # Raise an exception for HTTP errors
                return cast(Dict[str, Any], response.json())

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}: {e}")
            raise
        except httpx.RequestError as e:
            logger.exception(f"Request error occurred: {e}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    async def get_client_credentials_token(
        token_url: str, client_id: str, private_key: str, scope: str
    ) -> dict[str, Any]:
        """
        Perform OAuth2 client credentials flow using private_key_jwt authentication.

        Args:
            token_url: The OAuth2 token endpoint URL.
            client_id: The client ID.
            private_key: The private key in PEM format.
            scope: The scope for the token request.

        Returns:
            The token response as a dict.
        """
        now = int(time.time())
        payload = {
            "iss": client_id,
            "sub": client_id,
            "aud": token_url,
            "iat": now,
            "exp": now + 300,
            "jti": os.urandom(16).hex(),
        }
        # Use joserfc to encode JWT
        jwk = import_key(private_key, "RSA")
        client_assertion = joserfc.jwt.encode({"alg": "RS256"}, payload, jwk)
        form_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
            "scope": scope,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, headers=headers, data=form_data)
                logger.info(f"Response from client credentials: {response.text}")
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())
        except httpx.HTTPStatusError as e:
            # log the response text for debugging
            logger.error(f"HTTP error occurred: {e.response.text}: {e}")
            raise
        except httpx.RequestError as e:
            logger.exception(f"Request error occurred: {e}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def encode_state(content: dict[str, str]) -> str:
        """
        Encode the state content into a base64url encoded string.

        Args:
            content: The content to encode, typically a dictionary.

        Returns:
            A base64url encoded string of the content.
        """
        json_content = json.dumps(content)
        encoded_content = base64.urlsafe_b64encode(json_content.encode("utf-8")).decode(
            "utf-8"
        )
        return encoded_content.rstrip("=")

    @staticmethod
    def decode_state(encoded_content: str) -> dict[str, str]:
        """
        Decode a base64url encoded string back into its original dictionary form.

        Args:
            encoded_content: The base64url encoded string to decode.

        Returns:
            The decoded content as a dictionary.
        """
        padding_needed = 4 - (len(encoded_content) % 4)
        if padding_needed < 4:
            encoded_content += "=" * padding_needed
        json_content = base64.urlsafe_b64decode(encoded_content).decode("utf-8")
        return cast(dict[str, str], json.loads(json_content))
