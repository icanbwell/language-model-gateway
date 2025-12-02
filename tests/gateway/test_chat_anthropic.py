from random import randint
from typing import Optional

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam

from language_model_gateway.configs.config_schema import ChatModelConfig, ModelConfig
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.asyncio
async def test_chat_completions(
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

    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="b_well_phr",
                name="ChatGPT",
                description="ChatGPT",
                type="openai",
                model=ModelConfig(provider="ollama"),
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
        "content": "I'm 60 years old and have been programming for 5 days.",
    }
    chat_id: str = str(randint(1, 1000))
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
        extra_headers={"X-Chat-Id": chat_id, "x-openwebui-user-id": "test_user_id"},
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )

    assert content is not None
    print(content)
    # assert "Barack" in content

    message = {
        "role": "user",
        "content": "let’s talk about football",
    }
    chat_completion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
        extra_headers={"X-Chat-Id": chat_id, "x-openwebui-user-id": "test_user_id"},
    )

    # print the top "choice"
    content = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )

    assert content is not None

    message = {
        "role": "user",
        "content": "look up my user profile",
    }
    chat_completion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
        extra_headers={"X-Chat-Id": chat_id, "x-openwebui-user-id": "test_user_id"},
    )

    # print the top "choice"
    content = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )

    assert content is not None


@pytest.mark.asyncio
async def test_chat_completions_with_chat_history(
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

    # Test health endpoint
    # response = await async_client.get("/health")
    # assert response.status_code == 200

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
                "content": "Who was the 44th president of United States? ",
            },
            {"role": "assistant", "content": "Barack Obama"},
            {
                "role": "user",
                "content": "what is his first name?",
            },
        ],
        model="General Purpose",
    )

    # print the top "choice"
    print("========  Response ======")
    print(chat_completion)
    print("====== End of Response ======")
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "Barack" in content
