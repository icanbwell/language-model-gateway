import os

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.responses import EasyInputMessageParam, ResponseTextDeltaEvent

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from oidcauthlib.auth.models.token import Token
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.auth.keycloak_helper import KeyCloakHelper
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_responses_api_with_mcp_google_drive(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    access_token: Token | None = KeyCloakHelper.get_keycloak_access_token(
        username="tester", password="password"
    )
    assert access_token is not None

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "ABCDGX Test File Shared With b.well"
                )
            ),
        )

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    url: str = "http://mcp_server_gateway:5000/google_drive/"
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_google_drive",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                tools=[
                    AgentConfig(
                        name="download_file_from_url",
                        url=url,  # Assumes MCP server is running locally
                        auth="jwt_token",
                    ),
                ],
            )
        ]
    )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # Change if your API runs on a different port
        http_client=async_client,
        default_headers={
            "Authorization": f"Bearer {access_token.token}",
        },
    )

    # Use the responses API instead of chat completions
    prompt: EasyInputMessageParam = {
        "content": "Download https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing",
        "role": "user",
        "type": "message",
    }
    stream = await client.responses.create(
        model="General Purpose",
        input=[prompt],
        stream=True,
        max_output_tokens=20,
    )
    content: str = ""
    i: int = 0
    async for chunk in stream:
        i += 1
        delta_content = (
            chunk.delta if isinstance(chunk, ResponseTextDeltaEvent) else None
        )
        content += delta_content or ""
        print(f"======== Chunk {i} ========")
        print(delta_content or "")
        print(f"\n{chunk}\n")
        print(f"====== End of Chunk {i} ======")

    print("======== Final Content ========")
    print(content)
    print("====== End of Final Content ======")

    assert "ABCDGX Test File Shared With b.well" in content

    await model_configuration_cache.clear()
