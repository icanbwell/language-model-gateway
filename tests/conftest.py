from typing import AsyncGenerator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from oidcauthlib.container.container_registry import ContainerRegistry
from oidcauthlib.container.interfaces import IContainer

from language_model_gateway.gateway.api import app
from tests.common import create_test_container


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with LifespanManager(app=app) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture(scope="function")
async def test_container() -> AsyncGenerator[IContainer, None]:
    test_container: IContainer = create_test_container()
    async with ContainerRegistry.override(container=test_container) as container:
        yield container
