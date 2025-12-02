from typing import Optional

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam
from pytest_httpx import HTTPXMock
import pytest

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.asyncio
async def test_chat_completions_b_well(
    async_client: httpx.AsyncClient, httpx_mock: HTTPXMock, test_container: IContainer
) -> None:
    print("")
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="ChatGPT",
                type="langchain",
                model=ModelConfig(provider="bedrock"),
            )
        ]
    )
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )
    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Say this is a test",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="Test Model",
    )
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    print(content)
    assert content is not None
    assert "test" in content
