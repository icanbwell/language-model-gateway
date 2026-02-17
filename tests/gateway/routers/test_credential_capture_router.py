import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx

from language_model_gateway.gateway.routers.credential_capture_router import (
    CredentialCaptureRouter,
    CredentialSubmission,
)


@pytest.mark.asyncio
async def test_render_form_returns_html() -> None:
    app = FastAPI()
    app.include_router(CredentialCaptureRouter().get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/auth/credential-capture")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


@pytest.mark.asyncio
async def test_submit_form_invokes_callback() -> None:
    captured: list[CredentialSubmission] = []

    async def callback(submission: CredentialSubmission) -> JSONResponse:
        captured.append(submission)
        return JSONResponse({"received": True})

    app = FastAPI()
    app.include_router(CredentialCaptureRouter(callback=callback).get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/credential-capture",
            data={"username": "demo", "password": "secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert len(captured) == 1
    assert captured[0].username == "demo"
    assert captured[0].password == "secret"
