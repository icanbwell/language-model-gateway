import os

import httpx
import respx
from fastapi.testclient import TestClient
from httpx import Response

from language_model_gateway.gateway.api import app, create_app
from urllib.parse import urlparse, parse_qs


def test_login_route() -> None:
    client = TestClient(app)

    response = client.get("/login", follow_redirects=False)
    # Should redirect to Google OAuth
    assert response.status_code in (302, 307)
    assert "location" in response.headers
    print(response.headers["location"])
    assert (
        "/callback" in response.headers["location"]
        or "keycloak" in response.headers["location"]
    )


def test_callback_route() -> None:
    well_known_url = os.getenv("AUTH_WELL_KNOWN_URI")
    client_id = os.getenv("AUTH_CLIENT_ID")
    redirect_uri = os.getenv("AUTH_REDIRECT_URI")

    with respx.mock() as mock:
        client = TestClient(create_app())

        # use respx to mock the OAuth flow using the well-known URL
        mock.get(well_known_url).mock(
            return_value=Response(
                200,
                json={
                    "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
                    "token_endpoint": "https://oauth2.googleapis.com/token",
                    "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
                },
            )
        )
        # mock the endpoints for the OAuth flow
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
        response = client.get("/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "location" in response.headers
        location = response.headers["location"]

        parsed_url = urlparse(location)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get("state", [None])[0]
        code = query_params.get("code", [None])[0]

        # mock the redirect to the authorization endpoint
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

        # now mock the token endpoint to return a mock token when the requests passed 'grant_type=authorization_code&redirect_uri=http%3A%2F%2Ftestserver%2Fcallback'
        mock.post(
            "https://oauth2.googleapis.com/token",
            # params={
            #     "grant_type": "authorization_code",
            #     "redirect_uri": redirect_uri,
            #     "client_id": client_id,
            #     "code": code,
            # },
        ).mock(
            return_value=Response(
                200,
                json={
                    "access_token": "mock_access_token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )
        # now call /callback and pass the state and code parameters
        if not state:
            raise ValueError("State must be provided for the callback test")
        response = client.get(
            "/callback",
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
