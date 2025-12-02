import httpx
import pytest
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

from language_model_gateway.configs.config_schema import ChatModelConfig, ModelConfig
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)


@pytest.mark.asyncio
async def test_chat_completions(
    async_client: httpx.AsyncClient, test_container: IContainer
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
                model=ModelConfig(provider="ollama"),
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
        "content": "what is the first name of Obama?",
    }
    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        messages=[message],
        model="Test Model",
        stream=True,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        content += delta_content or ""
    print(content)
    assert "Barack" in content


@pytest.mark.asyncio
async def test_chat_completions_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
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
                model=ModelConfig(provider="ollama"),
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
        "content": "what is the first name of Obama?",
    }
    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        messages=[message],
        model="Test Model",
        stream=True,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        content += delta_content or ""
    print(content)
    assert "Barack" in content


@pytest.mark.asyncio
async def test_chat_completions_with_chat_history_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
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
                model=ModelConfig(provider="ollama"),
            )
        ]
    )
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )
    message1: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Who was the 44th president of United States? ",
    }
    message2: ChatCompletionAssistantMessageParam = {
        "role": "assistant",
        "content": "Barack Obama",
    }
    message3: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "what is his first name?",
    }
    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        messages=[
            message1,
            message2,
            message3,
        ],
        model="Test Model",
        stream=True,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        content += delta_content or ""
    print(content)
    assert "Barack" in content
