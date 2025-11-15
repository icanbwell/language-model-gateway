import os
from pathlib import Path

import httpx
import pytest

from oidcauthlib.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_image_generator import MockImageGenerator
from tests.gateway.mocks.mock_image_generator_factory import MockImageGeneratorFactory
from tests.gateway.mocks.mock_model_factory import MockModelFactory


@pytest.mark.asyncio
async def test_chat_anthropic_image_download(async_client: httpx.AsyncClient) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container: SimpleContainer = await get_container_async()
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )
        test_container.register(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
        )

    file_path = Path(os.environ["IMAGE_GENERATION_PATH"]).joinpath("foo.png")
    print(f"Writing to {file_path}")
    # Save image locally
    with open(file_path, "wb") as f:
        f.write(b"image content")

    # init client and connect to localhost server
    response = await async_client.request(
        "GET",
        "http://localhost:5000/image_generation/foo.png",
    )

    # call API
    assert response.status_code == 200
    assert response.content == b"image content"
