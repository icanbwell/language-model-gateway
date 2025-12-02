from typing import cast

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.responses import EasyInputMessageParam, Response, ResponseInputParam

from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.asyncio
async def test_openai_responses(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "Barack"
                )
            ),
        )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompt: EasyInputMessageParam = {
        "content": "I'm 60 years old and have been programming for 5 days.",
        "role": "user",
        "type": "message",
    }
    response: Response = await client.responses.create(
        model="General Purpose",
        input=[prompt],
        max_output_tokens=20,
    )
    content: str = response.output_text if response.output else ""
    assert content is not None
    print(content)

    prompt = {
        "content": "let’s talk about football",
        "role": "user",
        "type": "message",
    }
    response = await client.responses.create(
        model="General Purpose",
        input=[prompt],
        max_output_tokens=20,
    )
    content = response.output_text if response.output else ""
    assert content is not None

    prompt = {
        "content": "look up my user profile",
        "role": "user",
        "type": "message",
    }
    response = await client.responses.create(
        model="General Purpose",
        input=[prompt],
        max_output_tokens=20,
    )
    content = response.output_text if response.output else ""
    assert content is not None


@pytest.mark.asyncio
async def test_openai_responses_with_history(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "Barack"
                )
            ),
        )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompts: list[EasyInputMessageParam] = [
        {
            "content": "Who was the 44th president of United States?",
            "role": "user",
            "type": "message",
        },
        {
            "content": "Barack Obama",
            "role": "assistant",
            "type": "message",
        },
        {
            "content": "what is his first name?",
            "role": "user",
            "type": "message",
        },
    ]

    response: Response = await client.responses.create(
        model="General Purpose",
        input=cast(ResponseInputParam, prompts),
        max_output_tokens=20,
    )
    print("========  Response ======")
    print(response)
    print("====== End of Response ======")
    content: str = response.output_text if response.output_text else ""
    assert content is not None
    print("======= Response Content =======")
    print(content)
    print("==== End of Response Content ====")
    assert "Barack" in content
