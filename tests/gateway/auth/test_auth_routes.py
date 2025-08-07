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
    # This will fail unle   ss a valid OAuth flow is completed, but we can check for error response
    response = client.get("/callback")
    # Should return 400 or 422 due to missing params
    assert response.status_code in (400, 422)
    assert response.json() or response.text
