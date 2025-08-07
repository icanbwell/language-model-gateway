from fastapi.testclient import TestClient
from language_model_gateway.gateway.api import app

client = TestClient(app)


def test_login_route() -> None:
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
    # first call to /login to set up the session
    response = client.get("/login", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "location" in response.headers
    location = response.headers["location"]
    # extract the state and code parameters from the URL
    from urllib.parse import urlparse, parse_qs

    parsed_url = urlparse(location)
    query_params = parse_qs(parsed_url.query)
    state = query_params.get("state", [None])[0]
    code = query_params.get("code", [None])[0]
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
    assert response.json() or response.text
