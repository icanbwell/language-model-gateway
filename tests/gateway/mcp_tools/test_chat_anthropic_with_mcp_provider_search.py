import os
from typing import Optional

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer
from tests.common import get_test_container


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_chat_completions_with_mcp_provider_search(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    test_container: IContainer = get_test_container()
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
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="general_purpose",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                tools=[
                    AgentConfig(
                        name="mcp_provider_search",
                        url="http://provider_search:8001/mcp/",
                    ),
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
    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "what's address for Dr. Alice Smith?",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "123 Main St, Springfield" in content
