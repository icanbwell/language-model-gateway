import os
from typing import Dict, Any, List, Optional

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
from openai import AsyncOpenAI
from openai.types.responses import Response
from openai.types.responses.tool_param import Mcp

from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)
from fastmcp import Client
from fastmcp.client.client import CallToolResult


async def test_mcp_agent_directly() -> None:
    # HTTP server
    client: Client[Any] = Client(
        "http://mcp_server_gateway:5000/math_server/math_server"
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
        result: CallToolResult = await client.call_tool("add", {"a": 12, "b": 8})
        print(result)
        content: (
            TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource
        ) = result.content[0]
        assert content is not None
        assert isinstance(content, TextContent)
        assert content.text == "20"


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
            "math": {
                # make sure you start your weather server on port 8000
                "url": "http://math_server:8000/mcp/",
                "transport": "streamable_http",
            },
            "providersearch": {
                # make sure you start your weather server on port 8000
                "url": "http://provider_search:8001/mcp/",
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
    prompt = {"messages": "what's address for Dr. Alice Smith?"}
    # noinspection PyTypeChecker
    math_response = await graph.ainvoke(prompt)  # type: ignore[arg-type]
    print(math_response)
    print("=== Math Response ===")
    print(math_response["messages"][-1].content)
    print("===== End of Math Response =====")
    assert "123 Main St, Springfield" in math_response["messages"][-1].content
    # weather_response = await graph.ainvoke({"messages": "what is the weather in nyc?"})
    # print(weather_response)


async def test_mcp_agent_via_openai() -> None:
    # uses the OpenAI API to call the MCP server
    openai_api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY environment variable is not set"

    client = AsyncOpenAI(api_key=openai_api_key)

    tool: Mcp = {
        "type": "mcp",
        "server_label": "math_server",
        "server_url": "http://mcp_server_gateway:5051/math_server/math_server",
        "require_approval": "never",
    }
    resp: Response = await client.responses.create(
        model="gpt-4.1",
        tools=[tool],
        input="multiple 2 and 3 using math server",
    )

    print(resp.output_text)
