from typing import Optional

import httpx
from httpx import Response
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pytest_httpx import HTTPXMock

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
    PromptConfig,
    ModelParameterConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)


async def test_chat_completions_b_well(
    async_client: httpx.AsyncClient, httpx_mock: HTTPXMock
) -> None:
    print("")
    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        httpx_mock.add_callback(
            callback=lambda request: Response(
                200,
                json={
                    "id": "chat_1",
                    "object": "chat.completion",
                    "created": 1633660000,
                    "model": "b.well PHR",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "index": 0,
                            "message": {
                                "content": "This is a test",
                                "role": "assistant",
                            },
                        }
                    ],
                },
            ),
            url="http://host.docker.internal:5055/api/v1/chat/completions",
        )
    else:
        return  # this test only works with AI Agent

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="b.well",
                name="b.well PHR",
                description="Conversational PHR",
                type="openai",
                url="http://host.docker.internal:5055/api/v1/chat/completions",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="Use the patient id eEooRVLYdWIW753OhZUd1dgxQRny4KCo6fiH-13lY0043",
                    )
                ],
                model_parameters=[ModelParameterConfig(key="temperature", value=0)],
                tools=[
                    AgentConfig(name="current_date"),
                    AgentConfig(name="get_web_page"),
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
                "content": "Say this is a test",
            }
        ],
        model="b.well PHR",
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    print(content)
