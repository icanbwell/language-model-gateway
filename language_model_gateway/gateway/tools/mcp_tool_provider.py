from typing import Dict, List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection

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

    async def get_tools_by_url_async(self, *, tool: AgentConfig) -> List[BaseTool]:
        try:
            url: str | None = tool.url
            assert url is not None, "Tool URL must be provided"
            # first see if the url is already loaded
            if url in self.tools_by_mcp_url:
                return self.tools_by_mcp_url[url]

            mcp_tool_config: StreamableHttpConnection = {
                # make sure you start your weather server on port 8000
                "url": url,
                "transport": "streamable_http",
            }
            if tool.headers:
                mcp_tool_config["headers"] = tool.headers

            client: MultiServerMCPClient = MultiServerMCPClient(
                {
                    f"{tool.name}": mcp_tool_config,
                }
            )
            tools: List[BaseTool] = await client.get_tools()
            self.tools_by_mcp_url[url] = tools
            return tools
        except Exception as e:
            raise ValueError(f"Failed to load tools from MCP URL {tool.url}: {e}")

    async def get_tools_async(self, *, tools: list[AgentConfig]) -> list[BaseTool]:
        # get list of tools from the tools from each agent and then concatenate them
        all_tools: List[BaseTool] = []
        for tool in tools:
            if tool.url is not None:
                try:
                    tools_by_url: List[BaseTool] = await self.get_tools_by_url_async(
                        tool=tool
                    )
                    all_tools.extend(tools_by_url)
                except Exception as e:
                    raise ValueError(
                        f"Failed to get tools from MCP URL {tool.url}: {e}"
                    )
        return all_tools
