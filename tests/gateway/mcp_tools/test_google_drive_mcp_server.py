from typing import List
import pytest
import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam
from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from language_model_gateway.container.container_factory import ConfigExpiringCache
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from language_model_gateway.gateway.utilities.expiring_cache import ExpiringCache
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory


@pytest.mark.asyncio
async def test_chat_completions_with_mcp_google_drive(
    async_client: httpx.AsyncClient,
) -> None:
    test_container: SimpleContainer = await get_container_async()
    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "This is a mock response from the LLM."
                )
            ),
        )

    # set the model configuration for this test
    model_configuration_cache: ExpiringCache[List[ChatModelConfig]] = (
        test_container.resolve(ConfigExpiringCache)
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_google_drive",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="openai",
                    model="gpt-3.5-turbo",
                ),
                tools=[
                    AgentConfig(
                        name="download_file_from_url",
                        url="http://mcp_server_gateway:5051/google_drive/",  # Assumes MCP server is running locally
                    ),
                ],
            )
        ]
    )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # Change if your API runs on a different port
        http_client=async_client,
    )

    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Download https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
    )
    assert chat_completion.choices[0].message.content is not None

    await model_configuration_cache.clear()
