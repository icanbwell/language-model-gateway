import asyncio
from typing import override

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import (
    _list_all_tools,
    convert_mcp_tool_to_langchain_tool,
)
from mcp import ClientSession
from langchain_mcp_adapters.sessions import Connection, create_session


class MultiServerMCPClientWithCaching(MultiServerMCPClient):  # type: ignore[misc]
    @override
    async def get_tools(self, *, server_name: str | None = None) -> list[BaseTool]:
        """Get a list of all tools from all connected servers.

        Args:
            server_name: Optional name of the server to get tools from.
                If None, all tools from all servers will be returned (default).

        NOTE: a new session will be created for each tool call

        Returns:
            A list of LangChain tools

        """
        if server_name is not None:
            if server_name not in self.connections:
                msg = f"Couldn't find a server with name '{server_name}', expected one of '{list(self.connections.keys())}'"
                raise ValueError(msg)
            return await self.load_mcp_tools(
                None, connection=self.connections[server_name]
            )

        all_tools: list[BaseTool] = []
        load_mcp_tool_tasks = []
        for connection in self.connections.values():
            load_mcp_tool_task = asyncio.create_task(
                self.load_mcp_tools(None, connection=connection)
            )
            load_mcp_tool_tasks.append(load_mcp_tool_task)
        tools_list = await asyncio.gather(*load_mcp_tool_tasks)
        for tools in tools_list:
            all_tools.extend(tools)
        return all_tools

    @staticmethod
    async def load_mcp_tools(
        session: ClientSession | None,
        *,
        connection: Connection | None = None,
    ) -> list[BaseTool]:
        """Load all available MCP tools and convert them to LangChain tools.

        Args:
            session: The MCP client session. If None, connection must be provided.
            connection: Connection config to create a new session if session is None.

        Returns:
            List of LangChain tools. Tool annotations are returned as part
            of the tool metadata object.

        Raises:
            ValueError: If neither session nor connection is provided.
        """
        if session is None and connection is None:
            msg = "Either a session or a connection config must be provided"
            raise ValueError(msg)

        if session is None:
            # If a session is not provided, we will create one on the fly
            async with create_session(connection) as tool_session:
                await tool_session.initialize()
                tools = await _list_all_tools(tool_session)
        else:
            tools = await _list_all_tools(session)

        return [
            convert_mcp_tool_to_langchain_tool(session, tool, connection=connection)
            for tool in tools
        ]
