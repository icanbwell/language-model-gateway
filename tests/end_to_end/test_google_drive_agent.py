import os
from typing import Dict, Any, List

import mcp
from authlib.oauth2.rfc6749 import OAuth2Token
from fastmcp.client import StreamableHttpTransport
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import tools_condition
from mcp.types import (
    Prompt,
    Resource,
    Tool,
    TextContent,
    ImageContent,
    AudioContent,
    ResourceLink,
    EmbeddedResource,
)

from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)
from fastmcp import Client
from fastmcp.client.logging import LogMessage
import requests
from authlib.integrations.requests_client import OAuth2Session
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from typing import Optional

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory


def get_access_token(username: str, password: str) -> Dict[str, Any]:
    """
    Fetch an OAuth2 access token using Resource Owner Password Credentials grant.
    Args:
        username (str): The user's username.
        password (str): The user's password.
    Returns:
        dict: The token response.
    """
    OAUTH_CLIENT_ID = "bwell-client-id"
    # OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "bwell-secret")
    OAUTH_CLIENT_SECRET = "bwell-secret"
    OPENID_PROVIDER_URL = os.getenv(
        "OPENID_PROVIDER_URL",
        "http://keycloak:8080/realms/bwell-realm/.well-known/openid-configuration",
    )

    resp = requests.get(OPENID_PROVIDER_URL, timeout=5)
    resp.raise_for_status()
    openid_config = resp.json()
    token_endpoint = openid_config["token_endpoint"]

    # https://docs.authlib.org/en/latest/client/oauth2.html
    client = OAuth2Session(
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        # scope="openid email offline_access",
    )

    try:
        # Acquire token using client_credentials grant
        client_credentials_token = client.fetch_token(
            url=token_endpoint,
            grant_type="client_credentials",
        )
        print(
            f"Client credentials token fetched successfully: {client_credentials_token}"
        )
    except Exception as e:
        print(f"Error fetching client_credentials token: {e}")
        raise
    try:
        token: dict[str, str] | OAuth2Token = client.fetch_token(
            url=token_endpoint,
            username=username,
            password=password,
            grant_type="password",
        )
    except Exception as e:
        print(f"Error fetching access token: {e}")
        raise
    return token if isinstance(token, dict) else token["access_token"]


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_google_drive_mcp_agent_directly() -> None:
    # HTTP server
    access_token_result: Dict[str, str] = get_access_token(
        username="tester", password="password"
    )
    url: str = "http://mcp_server_gateway:5000/google_drive"
    access_token = access_token_result["access_token"]
    transport: StreamableHttpTransport = StreamableHttpTransport(
        url=url, auth=access_token
    )

    async def log_handler(message: LogMessage) -> None:
        if message.level == "error":
            print(f"ERROR: {message.data}")
        elif message.level == "warning":
            print(f"WARNING: {message.data}")
        else:
            print(f"{message.level.upper()}: {message.data}")

    async def progress_handler(
        progress: float, total: float | None, message: str | None
    ) -> None:
        if total is not None:
            percentage = (progress / total) * 100
            print(f"Progress: {percentage:.1f}% - {message or ''}")
        else:
            print(f"Progress: {progress} - {message or ''}")

    client: Client[Any] = Client(
        transport=transport,
        log_handler=log_handler,
        progress_handler=progress_handler,
    )
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        tools: List[Tool] = await client.list_tools()
        assert tools is not None
        resources: List[Resource] = await client.list_resources()
        assert resources is not None
        prompts: List[Prompt] = await client.list_prompts()
        assert prompts is not None

        # Execute operations
        result: mcp.types.CallToolResult = await client.call_tool_mcp(
            "download_file_from_url",
            {
                "url": "https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing"
            },
        )
        print(result)
        content: (
            TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource
        ) = result.content[0]
        assert content is not None
        assert isinstance(content, TextContent)
        assert "Hello, this is a test file shared with all of b.well" in content.text


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_google_drive_via_llm() -> None:
    verify_aws_boto3_authentication()
    # model: BaseChatModel = init_chat_model("openai:gpt-4.1")
    model_parameters_dict: Dict[str, Any] = {}
    access_token_result: Dict[str, str] = get_access_token(
        username="tester", password="password"
    )
    url: str = "http://mcp_server_gateway:5000/google_drive"
    access_token = access_token_result["access_token"]

    model: BaseChatModel = ChatBedrockConverse(
        client=None,
        # model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        provider="anthropic",
        credentials_profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        # Setting temperature to 0 for deterministic results
        **model_parameters_dict,
    )
    mcp_tool_config: StreamableHttpConnection = {
        "url": url,
        "transport": "streamable_http",
        # specify the http client factory to use the headers
        # httpx_client_factory
        # and/or bearer "auth"# auth: NotRequired[httpx.Auth]
        "headers": {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    }

    client = MultiServerMCPClient(
        {
            "download_file_from_url": mcp_tool_config,
        }
    )
    tools = await client.get_tools()

    def call_model(state: MessagesState) -> Dict[str, BaseMessage]:
        response = model.bind_tools(tools).invoke(state["messages"])
        return {"messages": response}

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(StreamingToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    graph = builder.compile()
    prompt = {
        "messages": "show me contents of this file: https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing"
    }
    # noinspection PyTypeChecker
    math_response = await graph.ainvoke(prompt)  # type: ignore[arg-type]
    print(math_response)
    print("=== Google Drive Response ===")
    print(math_response["messages"][-1].content)
    print("===== End of Math Response =====")
    assert (
        "Hello, this is a test file shared with all of b.well"
        in math_response["messages"][-1].content
    )
    # weather_response = await graph.ainvoke({"messages": "what is the weather in nyc?"})
    # print(weather_response)


def verify_aws_boto3_authentication() -> None:
    """
    Test if AWS credentials are configured and boto3 can authenticate.
    Uses profile and region from environment variables if set.
    """
    credentials_profile_name = os.environ.get("AWS_CREDENTIALS_PROFILE")
    region_name = os.environ.get("AWS_REGION", "us-east-1")
    session_kwargs = {}
    if credentials_profile_name:
        session_kwargs["profile_name"] = credentials_profile_name
    if region_name:
        session_kwargs["region_name"] = region_name
    try:
        session = boto3.Session(**session_kwargs)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"AWS authentication successful: {identity}")
        assert "Account" in identity
    except NoCredentialsError:
        print("AWS credentials not found.")
        assert False, "AWS credentials not found."
    except ClientError as e:
        print(f"AWS client error: {e}")
        assert False, f"AWS client error: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        assert False, f"Unexpected error: {e}"


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_chat_completions_with_google_drive(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    access_token_result: Dict[str, str] = get_access_token(
        username="tester", password="password"
    )
    url: str = "http://mcp_server_gateway:5000/google_drive"
    access_token = access_token_result["access_token"]

    test_container: SimpleContainer = await get_container_async()
    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "Hello, this is a test file shared with all of b.well"
                )
            ),
        )
    else:
        verify_aws_boto3_authentication()

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="google_drive",
                name="Google Drive",
                description="Google Drive",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                tools=[
                    AgentConfig(
                        name="google_drive", tools="download_file_from_url", url=url
                    ),
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

    # call API
    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "show me contents of this file: https://docs.google.com/document/d/15uw9_mdTON6SQpQHCEgCffVtYBg9woVjvcMErXQSaa0/edit?usp=sharing",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="Google Drive",
        extra_headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "Hello, this is a test file shared with all of b.well" in content
