import os
from typing import Dict, List, Iterable

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from openai.types.chat import ChatCompletionToolParam

from language_model_gateway.configs.config_schema import AgentConfig


class MCPToolProvider:
    """
    A class to provide tools for the MCP (Model Control Protocol) gateway.
    This class is responsible for managing and providing access to various tools
    that can be used in conjunction with the MCP.
    """

    def __init__(self) -> None:
        self.tools_by_mcp_url: Dict[str, List[BaseTool]] = {}

    async def load_async(self) -> None:
        pass

    async def get_tools_by_url_async(
        self, *, tool: AgentConfig, headers: Dict[str, str]
    ) -> List[BaseTool]:
        try:
            url: str | None = tool.url
            assert url is not None, "Tool URL must be provided"
            # first see if the url is already loaded
            if url in self.tools_by_mcp_url:
                return self.tools_by_mcp_url[url]

            # TODO: probably cache the tools and just use the headers by specifying an httpx_client_factory
            mcp_tool_config: StreamableHttpConnection = {
                "url": url,
                "transport": "streamable_http",
                # specify the http client factory to use the headers
                # httpx_client_factory
                # and/or bearer "auth"# auth: NotRequired[httpx.Auth]
            }
            if tool.headers:
                # replace the strings with os.path.expandvars # to allow for environment variable expansion
                mcp_tool_config["headers"] = {
                    key: os.path.expandvars(value)
                    for key, value in tool.headers.items()
                }

            # pass Authorization header if provided
            if headers and "authorization" in headers:
                # add the Authorization header to the mcp_tool_config headers
                mcp_tool_config["headers"] = {
                    **mcp_tool_config.get("headers", {}),
                    "Authorization": headers["authorization"],
                }

            client: MultiServerMCPClient = MultiServerMCPClient(
                {
                    f"{tool.name}": mcp_tool_config,
                }
            )
            tools: List[BaseTool] = await client.get_tools()
            if tool.tool_name and tools:
                # filter tools by tool_name if provided
                tools = [t for t in tools if t.name == tool.tool_name]
            self.tools_by_mcp_url[url] = tools
            return tools
        except Exception as e:
            raise ValueError(f"Failed to load tools from MCP URL {tool.url}: {e}")

    async def get_tools_async(
        self, *, tools: list[AgentConfig], headers: Dict[str, str],
           tools_in_request: Iterable[ChatCompletionToolParam] | None
    ) -> list[BaseTool]:
        # get list of tools from the tools from each agent and then concatenate them
        all_tools: List[BaseTool] = []
        for tool in tools:
            if tool.url is not None:
                try:
                    tools_by_url: List[BaseTool] = await self.get_tools_by_url_async(
                        tool=tool, headers=headers
                    )
                    all_tools.extend(tools_by_url)
                except Exception as e:
                    raise ValueError(
                        f"Failed to get tools from MCP URL {tool.url}: {e}"
                    )
        # now add the tools in the request if provided
        if tools_in_request:
            for tool_in_request in tools_in_request:
                try:
                    tools_by_url: List[BaseTool] = await self.get_tools_by_url_async(
                        tool=AgentConfig(
                            name=tool_in_request.name,
                            url=tool_in_request.ser,
                            tool_name=tool_in_request.tool_name,
                            headers=tool_in_request.headers or {},
                        ), headers=headers
                    )
                    all_tools.extend(tools_by_url)
                except Exception as e:
                    raise ValueError(
                        f"Failed to get tools from MCP URL {tool.url}: {e}"
                    )
        return all_tools
