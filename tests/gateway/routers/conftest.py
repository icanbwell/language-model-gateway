"""
Minimal FastAPI app fixture for CodingModelRouter tests.

Creates an app with only CodingModelRouter registered, avoiding the full
application startup (which requires databricks SDK and other optional deps).
"""

from typing import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI

from language_model_gateway.gateway.routers.model_routing.router import (
    CodingModelRouter,
)


@pytest.fixture
async def router_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    app = FastAPI()
    app.include_router(CodingModelRouter().get_router())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
