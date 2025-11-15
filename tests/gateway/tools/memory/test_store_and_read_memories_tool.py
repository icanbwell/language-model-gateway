from typing import Optional, List

import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion import Choice

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
)
from oidcauthlib.auth.models.token import Token
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from oidcauthlib.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.auth.keycloak_helper import KeyCloakHelper
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_image_generator import MockImageGenerator
from tests.gateway.mocks.mock_image_generator_factory import MockImageGeneratorFactory
from tests.gateway.mocks.mock_model_factory import MockModelFactory


async def test_store_and_read_memories_tool(async_client: httpx.AsyncClient) -> None:
    print("")
    access_token: Token | None = KeyCloakHelper.get_keycloak_access_token(
        username="tester", password="password"
    )
    assert access_token is not None
    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "tester-subject-id profile diabetes"
                )
            ),
        )
        test_container.register(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
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
            )
        ]
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
    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "I have diabetes. Also return what tools you have access to and why you chose not to use each tool.",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
        extra_headers={
            "Authorization": f"Bearer {access_token.token}",
        },
    )

    print(chat_completion)

    # print the top "choice"
    choices: List[Choice] = chat_completion.choices
    print(choices)
    content: Optional[str] = ",".join(
        [choice.message.content or "" for choice in choices]
    )
    assert content is not None
    print("======== Final Content ========")
    print(content)
    print("====== End of Final Content ======")
    assert "profile" in content

    message2: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Show me my user profile. Also return what tools you have access to and why you chose not to use each tool.",
    }
    chat_completion2: ChatCompletion = await client.chat.completions.create(
        messages=[message2],
        model="General Purpose",
        extra_headers={
            "Authorization": f"Bearer {access_token.token}",
        },
    )

    choices2: List[Choice] = chat_completion2.choices
    print(choices2)
    content2: Optional[str] = ",".join(
        [choice.message.content or "" for choice in choices2]
    )
    assert content2 is not None
    print("======== Final Content ========")
    print(content2)
    print("====== End of Final Content ======")
    assert "tester-subject-id" in content2

    message3: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Show me my memories.  Also return what tools you have access to and why you chose not to use each tool.",
    }
    chat_completion3: ChatCompletion = await client.chat.completions.create(
        messages=[message3],
        model="General Purpose",
        extra_headers={
            "Authorization": f"Bearer {access_token.token}",
        },
    )

    choices3: List[Choice] = chat_completion3.choices
    print(choices3)
    content3: Optional[str] = ",".join(
        [choice.message.content or "" for choice in choices3]
    )
    assert content3 is not None
    print("======== Final Content ========")
    print(content3)
    print("====== End of Final Content ======")
    assert "diabetes" in content3
