import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import respx

from language_model_gateway.gateway.routers.app_login_router import (
    AppLoginRouter,
    CredentialSubmission,
)


@pytest.mark.asyncio
async def test_render_form_returns_html() -> None:
    app = FastAPI()
    app.include_router(AppLoginRouter().get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/app/login")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


@pytest.mark.asyncio
async def test_submit_form_invokes_callback() -> None:
    captured: list[CredentialSubmission] = []

    async def callback(
        submission: CredentialSubmission,
        *_: object,
    ) -> JSONResponse:
        captured.append(submission)
        return JSONResponse({"received": True})

    app = FastAPI()
    app.include_router(AppLoginRouter(callback=callback).get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/app/login",
            data={"username": "demo", "password": "secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert len(captured) == 1
    assert captured[0].username == "demo"
    assert captured[0].password == "secret"


@pytest.mark.asyncio
async def test_submit_form_default_callback_fetches_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_LOGIN_CLIENT_KEY", "test-client-key")

    app = FastAPI()
    app.include_router(AppLoginRouter().get_router())

    transport = httpx.ASGITransport(app=app)

    with respx.mock(assert_all_called=True) as router:
        router.post("https://api.dev.icanbwell.com/identity/account/login").respond(
            json={"accessToken": {"jwtToken": "abc.123"}},
            status_code=200,
        )

        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/app/login",
                data={"username": "user@example.com", "password": "pw"},
            )

    assert response.status_code == 200
    assert response.json() == {"accessToken": "abc.123"}
