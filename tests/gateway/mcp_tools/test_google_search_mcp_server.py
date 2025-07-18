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
async def test_chat_completions_with_mcp_google_search(
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
        test_container.resolve(ExpiringCache)
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="general_purpose",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="openai",
                    model="gpt-3.5-turbo",
                ),
                tools=[
                    AgentConfig(
                        name="mcp_google_search",
                        url="http://google_search:8002/mcp/",  # Assumes MCP server is running locally
                        headers={
                            "GOOGLE_API_KEY": "$GOOGLE_API_KEY",
                            "GOOGLE_CSE_ID": "$GOOGLE_CSE_ID",
                        },
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
        "content": "Search Google for 'OpenAI' and return the top result.",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
    )
    assert chat_completion.choices[0].message.content is not None
