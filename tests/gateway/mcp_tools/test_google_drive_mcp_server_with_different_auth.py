import os

import pytest
import httpx
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
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_chat_completions_with_mcp_google_drive_with_different_auth(
    async_client: httpx.AsyncClient,
) -> None:
    test_container: SimpleContainer = await get_container_async()
    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
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
    url: str = "http://mcp_server_gateway:5000/google_drive"
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_google_drive",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="openai",
                    model="gpt-3.5-turbo",
                ),
                tools=[
                    AgentConfig(
                        name="download_file_from_url",
                        url=url,  # Assumes MCP server is running locally
                        auth="jwt_token",
                        auth_audiences=["bwell-client-id-3"],
                    ),
                ],
            )
        ]
    )

    # do a password grant with keycloak to get a JWT token
    token_url = "http://keycloak:8080/realms/bwell-realm/protocol/openid-connect/token"  # Replace <realm-name> with your Keycloak realm
    data = {
        "grant_type": "password",
        "client_id": os.getenv("AUTH_CLIENT_ID"),  # Replace with your client_id
        "username": os.getenv("MY_USER_NAME"),  # Replace with your username
        "password": os.getenv("MY_USER_PASSWORD"),  # Replace with your password
        "client_secret": os.getenv("AUTH_CLIENT_SECRET"),  # Uncomment if needed
        "scope": "openid",  # Optional
    }
    jwt_token: str | None = None
    async with httpx.AsyncClient() as oidc_client:
        token_response = await oidc_client.post(token_url, data=data)
        token_response.raise_for_status()
        token_response_json = token_response.json()
        jwt_token = token_response_json["access_token"]

    assert jwt_token is not None
    client = AsyncOpenAI(
        api_key=jwt_token,
        base_url="http://localhost:5000/api/v1",  # Change if your API runs on a different port
        http_client=async_client,
    )

    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Download https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="General Purpose",
    )
    assert chat_completion.choices[0].message.content is not None

    assert (
        "ABCDGX Test File Shared With b.well"
        in chat_completion.choices[0].message.content
    )

    await model_configuration_cache.clear()
