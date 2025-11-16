import httpx
import pytest
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI
from openai.types import ImagesResponse, Image

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
async def test_chat_anthropic_image_generation(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )
        test_container.singleton(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
        )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # change the default port if needed
        http_client=async_client,
    )

    # call API
    response: ImagesResponse = await client.images.generate(
        model="dall-e-3",
        prompt="a white siamese cat",
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image: Image | None = response.data[0] if response.data else None
    assert image is not None
    image_url: str | None = image.url
    print(f"Image URL: {image_url}")
    assert image_url is not None
    assert "http" in image_url
