import os
from typing import Dict, Any, List

from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
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

from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)
from fastmcp import Client
from fastmcp.client.client import CallToolResult


async def test_google_drive_mcp_agent_directly() -> None:
    # HTTP server
    client: Client[Any] = Client("http://mcp_server_gateway:5000/google_drive")
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
        result: CallToolResult = await client.call_tool(
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
            "google_drive": {
                # make sure you start your weather server on port 8000
                "url": "http://mcp_server_gateway:5000/google_drive",
                "transport": "streamable_http",
            },
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
