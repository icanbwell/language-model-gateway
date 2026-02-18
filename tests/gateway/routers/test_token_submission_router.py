import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from oidcauthlib.container.inject import Inject

from language_model_gateway.gateway.managers.token_submission_manager import (
    TokenSubmissionManager,
)
from language_model_gateway.gateway.routers.token_submission_router import (
    TokenSubmissionRouter,
)
from language_model_gateway.gateway.models.token_submission import TokenSubmission


@pytest.mark.asyncio
async def test_render_form_returns_html() -> None:
    app = FastAPI()
    app.include_router(TokenSubmissionRouter().get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/app/token")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'name="token"' in response.text


@pytest.mark.asyncio
async def test_submit_form_invokes_callback() -> None:
    captured: list[TokenSubmission] = []

    app = FastAPI()
    app.include_router(TokenSubmissionRouter().get_router())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/app/token",
            params={
                "auth_provider": "demo",
                "referring_email": "user@example.com",
                "referring_subject": "subj",
            },
            data={"token": "abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert len(captured) == 1
    assert captured[0].token == "abc"


@pytest.mark.asyncio
async def test_submit_form_invokes_manager_dependency() -> None:
    class DummyManager:
        def __init__(self) -> None:
            self.called = False
            self.kwargs: dict[str, object] = {}

        async def submit_token(self, **kwargs: object) -> JSONResponse:
            self.called = True
            self.kwargs = kwargs
            return JSONResponse({"stored": True})

    manager = DummyManager()

    app = FastAPI()
    app.include_router(TokenSubmissionRouter().get_router())
    app.dependency_overrides[Inject(TokenSubmissionManager)] = lambda: manager

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/app/token",
            params={
                "auth_provider": "demo",
                "referring_email": "user@example.com",
                "referring_subject": "subject",
            },
            data={"token": "abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"stored": True}
    assert manager.called is True
    assert manager.kwargs["auth_provider"] == "demo"
    assert manager.kwargs["referring_subject"] == "subject"
