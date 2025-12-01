import httpx
import pytest
from openai import AsyncOpenAI

from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.asyncio
async def test_openai_responses_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompt = "what is the first name of Obama?"
    stream = await client.responses.create(
        model="General Purpose",
        input=prompt,
        stream=True,
        max_output_tokens=20,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        print(f"======== Chunk {i} ========")
        delta_content = getattr(chunk, "output_text", "")
        content += delta_content or ""
        print(delta_content or "")
        print(f"\n{chunk}\n")
        print(f"====== End of Chunk {i} ======")

    print("======== Final Content ========")
    print(content)
    print("====== End of Final Content ======")
    assert "Barack" in content


@pytest.mark.asyncio
async def test_responses_with_history_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompt = (
        "Who was the 44th president of United States?\n"
        "Barack Obama\n"
        "what is his first name?"
    )
    stream = await client.responses.create(
        model="gpt-3.5-turbo",  # model ignored as requested
        input=prompt,
        stream=True,
        max_output_tokens=20,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        print(f"======== Chunk {i} ========")
        delta_content = getattr(chunk, "output_text", "")
        content += delta_content or ""
        print(delta_content or "")
        print(f"====== End of Chunk {i} ======")

    print("======== Final Content ========")
    print(content)
    print("====== End of Final Content ======")
    assert "Barack" in content
