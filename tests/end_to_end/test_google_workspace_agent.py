import os
from typing import Dict, Any, Optional, List

import pytest
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import tools_condition
from mcp import ListToolsResult, types, Tool
from mcp.types import CallToolResult
from openai import AsyncOpenAI
from openai.types.responses import Response
from openai.types.responses.tool_param import Mcp

from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)

import logging
import sys

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("httpx")
logger.setLevel(logging.DEBUG)

# Add a stream handler to output httpx logs to stdout
httpx_logger = logging.getLogger("httpx")
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
stream_handler.setFormatter(formatter)
if not any(isinstance(h, logging.StreamHandler) for h in httpx_logger.handlers):
    httpx_logger.addHandler(stream_handler)


async def test_google_workspace_agent_directly() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    # Connect to a streamable HTTP server
    async with streamablehttp_client("http://google-workspace-mcp:8000/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            # List available tools
            tool_result: ListToolsResult = await session.list_tools()
            tools_tools: List[Tool] = tool_result.tools
            print(f"Available tools: {[tool.name for tool in tools_tools]}")

            result: CallToolResult = await session.call_tool(
                "search_drive_files",
                {
                    "query": "search google drive for a file named 'test.txt'.",
                    "user_google_email": "imran@icanbwell.com",
                },
            )
            for content in result.content:
                if isinstance(content, types.TextContent):
                    print(f"Text: {content.text}")


async def test_mcp_agent() -> None:
    # model: BaseChatModel = init_chat_model("openai:gpt-4.1")
    model_parameters_dict: Dict[str, Any] = {}

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

    client = MultiServerMCPClient(
        {
            # "math": {
            #     "command": "python",
            #     # Make sure to update to the full absolute path to your math_server.py file
            #     "args": ["./examples/math_server.py"],
            #     "transport": "stdio",
            # },
            # "math": {
            #     # make sure you start your weather server on port 8000
            #     "url": "http://mcp_server_gateway:5000/math_server",
            #     "transport": "streamable_http",
            # },
            # "providersearch": {
            #     # make sure you start your weather server on port 8000
            #     "url": "http://mcp_server_gateway:5000/provider_search",
            #     "transport": "streamable_http",
            # },
            "google_workspace": {
                "url": "http://google-workspace-mcp:8000/mcp",
                "transport": "streamable_http",
            }
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
        "messages": "search google drive for a file named 'test.txt'.  my email is imran@icanbwell.com."
    }
    # noinspection PyTypeChecker
    math_response = await graph.ainvoke(prompt)  # type: ignore[arg-type]
    print(math_response)
    print("=== Math Response ===")
    print(math_response["messages"][-1].content)
    print("===== End of Math Response =====")
    assert "123 Main St, Springfield" in math_response["messages"][-1].content
    # weather_response = await graph.ainvoke({"messages": "what is the weather in nyc?"})
    # print(weather_response)


@pytest.mark.skip(
    reason="This test requires opening a public MCP server per https://gofastmcp.com/integrations/openai"
)
async def test_mcp_agent_via_openai() -> None:
    # uses the OpenAI API to call the MCP server
    openai_api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY environment variable is not set"

    client = AsyncOpenAI(api_key=openai_api_key)

    tool: Mcp = {
        "type": "mcp",
        "server_label": "math_server",
        "server_url": "http://mcp_server_gateway:5000/math_server",
        "require_approval": "never",
    }
    resp: Response = await client.responses.create(
        model="gpt-4.1",
        tools=[tool],
        input="multiple 2 and 3 using math server",
    )

    print(resp.output_text)
