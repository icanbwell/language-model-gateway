"""
Tests for session_savings_router.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavings,
    TierSavings,
)
from language_model_gateway.gateway.routers.model_routing.session_savings_router import (
    SessionSavingsRouter,
)


def test_registers_savings_route() -> None:
    router = SessionSavingsRouter()
    paths = {r.path for r in router.get_router().routes if isinstance(r, APIRoute)}
    assert "/v1/model-routing/sessions/{session_id}/savings" in paths


@pytest.mark.asyncio
async def test_get_savings_returns_200_with_body() -> None:
    router = SessionSavingsRouter(mongo_uri="mongodb://localhost:27017")
    savings = SessionSavings(
        session_id="sess-1",
        total_savings_usd=0.42,
        total_tokens=12345,
        tiers={
            "low": TierSavings(
                model="qwen-coder",
                backend="aws_bedrock",
                cost_usd=0.10,
                anthropic_cost_usd=0.30,
            )
        },
    )
    app = FastAPI()
    app.include_router(router.get_router())

    with patch.object(
        router._reader, "get_session_savings", new=AsyncMock(return_value=savings)
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/model-routing/sessions/sess-1/savings")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "sess-1"
    assert body["total_savings_usd"] == 0.42
    assert body["tiers"]["low"]["cost_usd"] == 0.10


@pytest.mark.asyncio
async def test_get_savings_returns_404_when_not_found() -> None:
    router = SessionSavingsRouter(mongo_uri="mongodb://localhost:27017")
    app = FastAPI()
    app.include_router(router.get_router())

    with patch.object(
        router._reader, "get_session_savings", new=AsyncMock(return_value=None)
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/model-routing/sessions/unknown/savings")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_savings_returns_404_when_no_mongo_configured() -> None:
    router = SessionSavingsRouter(mongo_uri=None)
    app = FastAPI()
    app.include_router(router.get_router())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/model-routing/sessions/sess-1/savings")

    assert response.status_code == 404
