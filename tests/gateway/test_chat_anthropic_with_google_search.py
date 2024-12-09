from typing import Optional, List

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    ToolConfig,
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
async def test_chat_completions_with_web_search(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    test_container: SimpleContainer = await get_container_async()
    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "Donald Trump won the last US election"
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
                id="google_search",
                name="Google Search",
                description="Google Search",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                tools=[
                    ToolConfig(name="google_search"),
                    ToolConfig(name="get_web_page"),
                ],
            )
        ]
    )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # change the default port if needed
        http_client=async_client,
    )

    # call API
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Who won the last US election?",
            }
        ],
        model="Google Search",
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "Trump" in content
