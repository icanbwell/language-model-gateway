import httpx
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionUserMessageParam

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    ModelParameterConfig,
    PromptConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)


async def test_chat_completions_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    # Set the Test Model in the cache
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="Streaming Model",
                type="langchain",
                model=ModelConfig(provider="ollama"),
                model_parameters=[ModelParameterConfig(key="temperature", value=0.5)],
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="You are a streaming test model. Use best practices for streaming completions.",
                    )
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
    message1: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Say this is a test",
    }
    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        model="Test Model",
        messages=[message1],
        stream=True,
    )
    chunk: ChatCompletionChunk
    async for chunk in stream:
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        print(delta_content)
