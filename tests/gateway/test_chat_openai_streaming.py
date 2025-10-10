import json
import os
from typing import List

import httpx
import pytest
from httpx import Response
from openai import AsyncOpenAI, AsyncStream
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionChunk
from pytest_httpx import HTTPXMock, IteratorStream

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    ModelParameterConfig,
    PromptConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice


@pytest.mark.httpx_mock(
    should_mock=lambda request: os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1"
)
async def test_chat_completions_streaming(
    async_client: httpx.AsyncClient, httpx_mock: HTTPXMock
) -> None:
    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        chunks_json: List[ChatCompletionChunk] = [
            ChatCompletionChunk(
                id=str(0),
                created=1633660000,
                model="ChatGPT",
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(role="assistant", content="This" + " "),
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                ),
                object="chat.completion.chunk",
            ),
            ChatCompletionChunk(
                id=str(0),
                created=1633660000,
                model="ChatGPT",
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(role="assistant", content="is a" + " "),
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                ),
                object="chat.completion.chunk",
            ),
            ChatCompletionChunk(
                id=str(0),
                created=1633660000,
                model="ChatGPT",
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(role="assistant", content="test" + " "),
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                ),
                object="chat.completion.chunk",
            ),
        ]
        chunks: List[bytes] = [
            f"data: {json.dumps(chunks_json[0].model_dump())}\n\n".encode("utf-8"),
            f"data: {json.dumps(chunks_json[1].model_dump())}\n\n".encode("utf-8"),
            f"data: {json.dumps(chunks_json[2].model_dump())}\n\n".encode("utf-8"),
            b"data: [DONE]\n\n",
        ]
        httpx_mock.add_callback(
            callback=lambda request: Response(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                stream=IteratorStream(chunks),
            ),
            url="http://host.docker.internal:5055/api/v1/chat/completions",
        )

    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="b_well_phr",
                name="ChatGPT",
                description="ChatGPT",
                type="langchain",
                model=ModelConfig(
                    provider="openai",
                    model="gpt-4o",
                ),
                url="http://host.docker.internal:5055/api/v1/chat/completions",
                model_parameters=[ModelParameterConfig(key="temperature", value=0.5)],
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="Given a task description or existing prompt, produce a detailed system prompt",
                    ),
                    PromptConfig(
                        role="system",
                        content="The user will provide a Task, Goal, or Current Prompt.",
                    ),
                ],
                # tools=[
                #     ToolConfig(
                #         name="current_date"
                #     )
                # ]
            )
        ]
    )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # change the default port if needed
        http_client=async_client,
    )

    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        model="ChatGPT",
        messages=[{"role": "user", "content": "Say this is a test"}],
        stream=True,
    )

    chunk: ChatCompletionChunk
    async for chunk in stream:
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        print(delta_content)
