from typing import override, List, Dict

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection, create_session

# noinspection PyProtectedMember
from langchain_mcp_adapters.tools import (
    _list_all_tools,
    convert_mcp_tool_to_langchain_tool,
)
from mcp import ClientSession, Tool


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
            return self.create_tools_from_list(
                await self.load_metadata_for_mcp_tools(
                    None, connection=self.connections[server_name]
                ),
                session=None,
                connection=self.connections[server_name],
            )

        all_tools_metadata: Dict[str, list[Tool]] = {}
        for connection in self.connections.values():
            all_tools_metadata[
                connection["url"]
            ] = await self.load_metadata_for_mcp_tools(None, connection=connection)

        # create LangChain tools from the loaded MCP tools
        all_tools: List[BaseTool] = []
        for connection in self.connections.values():
            tools_for_connection = all_tools_metadata[connection["url"]]
            all_tools.extend(
                self.create_tools_from_list(
                    tools_for_connection, session=None, connection=connection
                )
            )
        return all_tools

    @staticmethod
    async def load_metadata_for_mcp_tools(
        session: ClientSession | None,
        *,
        connection: Connection | None = None,
    ) -> list[Tool]:
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
                tools: List[Tool] = await _list_all_tools(tool_session)
        else:
            tools = await _list_all_tools(session)
        return tools

    @staticmethod
    def create_tools_from_list(
        tools: list[Tool],
        session: ClientSession | None = None,
        connection: Connection | None = None,
    ) -> List[BaseTool]:
        return [
            convert_mcp_tool_to_langchain_tool(session, tool, connection=connection)
            for tool in tools
        ]
