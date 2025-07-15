from typing import Dict, List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from language_model_gateway.configs.config_schema import AgentConfig


class MCPToolProvider:
    """
    A class to provide tools for the MCP (Model Control Protocol) gateway.
    This class is responsible for managing and providing access to various tools
    that can be used in conjunction with the MCP.
    """

    def __init__(self) -> None:
        self.tools: Dict[str, BaseTool] = {}
        self._loaded: bool = False

    async def load_async(self) -> None:
        if not self._loaded:
            client: MultiServerMCPClient = MultiServerMCPClient(
                {
                    "math": {
                        "command": "python",
                        # Make sure to update to the full absolute path to your math_server.py file
                        "args": [
                            "/usr/src/language_model_gateway/language_model_gateway/gateway/tools/mcp/math_server.py"
                        ],
                        "transport": "stdio",
                    },
                    # "weather": {
                    #     # make sure you start your weather server on port 8000
                    #     "url": "http://localhost:8000/mcp/",
                    #     "transport": "streamable_http",
                    # },
                }
            )
            tools: List[BaseTool] = await client.get_tools()
            self.tools = {tool.name: tool for tool in tools}
            self._loaded = True

    def get_tool_by_name(self, *, tool: AgentConfig) -> BaseTool:
        if tool.name in self.tools:
            return self.tools[tool.name]
        raise ValueError(f"Tool with name {tool.name} not found")

    def has_tool(self, *, tool: AgentConfig) -> bool:
        return tool.name in self.tools

    def get_tools(self, *, tools: list[AgentConfig]) -> list[BaseTool]:
        return [
            self.get_tool_by_name(tool=tool)
            for tool in tools
            if self.has_tool(tool=tool)
        ]
