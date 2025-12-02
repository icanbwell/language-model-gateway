from typing import Optional

import httpx
import pytest
from oidcauthlib.container.interfaces import IContainer
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


@pytest.mark.asyncio
async def test_chat_completions_with_web_search(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="google_search",
                name="Google Search",
                description="Google Search",
                type="langchain",
                model=ModelConfig(provider="ollama"),
                tools=[
                    AgentConfig(name="google_search"),
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
    message1: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Who won the last US election?",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message1],
        model="Google Search",
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "Trump" in content
