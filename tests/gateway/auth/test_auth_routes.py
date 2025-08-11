import os
from typing import Dict, Any

import httpx
import respx
from fastapi.testclient import TestClient
from httpx import Response
from authlib.jose import jwk, jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from respx import MockRouter

from language_model_gateway.gateway.api import app, create_app
from urllib.parse import urlparse, parse_qs

from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)


def test_login_route() -> None:
    client = TestClient(app)

    response = client.get("/auth/login", follow_redirects=False)
    # Should redirect to Google OAuth
    assert response.status_code in (302, 307)
    assert "location" in response.headers
    print(response.headers["location"])
    assert (
        "/auth/callback" in response.headers["location"]
        or "keycloak" in response.headers["location"]
    )


def test_callback_route() -> None:
    well_known_url = os.getenv("AUTH_WELL_KNOWN_URI")
    client_id = os.getenv("AUTH_CLIENT_ID")
    redirect_uri = os.getenv("AUTH_REDIRECT_URI")

    mock: MockRouter | None = None
    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        mock = respx.mock().__enter__()

    try:
        jwk_private: Dict[str, Any] | None = None
        if mock is not None:
            # Generate RSA key pair using cryptography
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            # Convert to JWK using authlib
            jwk_private = jwk.dumps(private_bytes, kty="RSA")
            jwk_public = jwk.dumps(public_bytes, kty="RSA")
            jwks = {"keys": [jwk_public]}

            # Mock JWKS URI to return public key
            mock.get("https://openidconnect.googleapis.com/v1/jwks").mock(
                return_value=Response(200, json=jwks)
            )

        client = TestClient(create_app())

        if mock is not None:
            # use respx to mock the OAuth flow using the well-known URL
            mock.get(well_known_url).mock(
                return_value=Response(
                    200,
                    json={
                        "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
                        "token_endpoint": "https://oauth2.googleapis.com/token",
                        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
                        "jwks_uri": "https://openidconnect.googleapis.com/v1/jwks",
                    },
                )
            )
        # mock the endpoints for the OAuth flow`
        # this is the URL that the client will be redirected to for authentication
        # it should match the authorization_endpoint in the well-known configuration
        # and the client_id and redirect_uri should match the ones in the environment variables
        assert well_known_url is not None, (
            "AUTH_WELL_KNOWN_URI environment variable must be set"
        )
        assert client_id is not None, "AUTH_CLIENT_ID environment variable must be set"
        assert redirect_uri is not None, (
            "AUTH_REDIRECT_URI environment variable must be set"
        )
        # first call to /login to set up the session
        response = client.get("/auth/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "location" in response.headers
        location = response.headers["location"]

        parsed_url = urlparse(location)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get("state", [None])[0]
        code = query_params.get("code", [None])[0]
        nonce = query_params.get("nonce", [None])[0]

        # mock the redirect to the authorization endpoint
        if mock is not None:
            mock.get(
                location,
            ).mock(
                return_value=Response(
                    200,
                    json={
                        "code": code,
                        "state": state,
                    },
                )
            )
        # now navigate to the authorization endpoint using httpx client
        with httpx.Client() as httpx_client:
            httpx_response = httpx_client.get(
                location,
                follow_redirects=False,
            )
            assert httpx_response.status_code in (200, 302, 307)

        # Prepare claims for id_token
        if mock is not None:
            claims = {
                "iss": "https://accounts.google.com",
                "sub": "1234567890",
                "aud": client_id,
                "exp": 9999999999,
                "iat": 1111111111,
                "email": "tester@tester.com",
                "name": "John Doe",
                "nonce": nonce,  # This should match the nonce used in the authorization request
            }
            # Sign the id_token using the private key
            id_token = jwt.encode({"alg": "RS256"}, claims, jwk_private).decode()

            # Mock token endpoint to return signed id_token
            mock.post(
                "https://oauth2.googleapis.com/token",
            ).mock(
                return_value=Response(
                    200,
                    json={
                        "access_token": "mock_access_token",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "id_token": id_token,
                        "user_info": {
                            "sub": "1234567890",
                            "name": "John Doe",
                            "email": "tester@tester.com",
                            "picture": "http://example.com/john_doe.jpg",
                        },
                    },
                )
            )
        # now call /callback and pass the state and code parameters
        if not state:
            raise ValueError("State must be provided for the callback test")
        response = client.get(
            "/auth/callback",
            params={"state": state, "code": code},
            follow_redirects=False,
        )
        assert response.status_code == 200, (
            f"Unexpected status code: {response.status_code}"
        )
        assert "application/json" in response.headers.get("content-type", "")
        # Check if the response contains JSON data
        print(response.json())
        assert response.json()

    finally:
        if mock is not None:
            mock.__exit__(None, None, None)
