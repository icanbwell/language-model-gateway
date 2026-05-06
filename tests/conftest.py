from typing import AsyncGenerator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from simple_container.container.container_registry import ContainerRegistry
from simple_container.container.interfaces import IContainer

from language_model_gateway.gateway.api import app
from tests.common import create_test_container


@pytest.fixture(scope="function")
async def test_container() -> AsyncGenerator[IContainer, None]:
    test_container: IContainer = create_test_container()
    async with ContainerRegistry.override(container=test_container) as container:
        yield container


@pytest.fixture
async def async_client(
    test_container: IContainer,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with LifespanManager(app=app, startup_timeout=30) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app), base_url="http://test"
        ) as client:
            yield client
