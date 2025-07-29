import logging
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

logger = logging.getLogger(__name__)


class MultiServerMCPClientWithCaching(MultiServerMCPClient):  # type: ignore[misc]
    """A MultiServerMCPClient that caches tool metadata to avoid repeated calls to the MCP server.

    This class extends the MultiServerMCPClient to cache the metadata of tools
    across multiple calls to `get_tools`. It allows for efficient retrieval of tools
    without needing to repeatedly query the MCP server for the same tool metadata.
    """

    all_tools_metadata_cache: Dict[str, list[Tool]] = {}
    """Cache for all tools metadata across all servers.  url is connection URL of MCP server."""

    async def load_tools_metadata_cache(
        self, *, server_name: str | None = None
    ) -> None:
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
            connection_for_server = self.connections[server_name]
            if connection_for_server["url"] not in self.all_tools_metadata_cache:
                self.all_tools_metadata_cache[
                    connection_for_server["url"]
                ] = await self.load_metadata_for_mcp_tools(
                    None, connection=connection_for_server
                )
                logger.info(
                    f"Loaded tools for connection {connection_for_server['url']}"
                )
            else:
                logger.debug(
                    f"Tools for connection {connection_for_server['url']} are already cached"
                )
        else:
            for connection in self.connections.values():
                # if the tools for this connection are already cached, skip loading them
                if connection["url"] not in self.all_tools_metadata_cache:
                    self.all_tools_metadata_cache[
                        connection["url"]
                    ] = await self.load_metadata_for_mcp_tools(
                        None, connection=connection
                    )
                    logger.info(f"Loaded tools for connection {connection['url']}")
                else:
                    logger.debug(
                        f"Tools for connection {connection['url']} are already cached"
                    )

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

        await self.load_tools_metadata_cache(server_name=server_name)

        # create LangChain tools from the loaded MCP tools
        all_tools: List[BaseTool] = []
        for connection in self.connections.values():
            tools_for_connection = self.all_tools_metadata_cache[connection["url"]]
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
        """
        Create LangChain tools from a list of MCP tools.
        Args:
            tools: List of MCP tools to convert.
            session: The MCP client session. If None, connection must be provided.
            connection: Connection config to create a new session if session is None.
        """
        return [
            convert_mcp_tool_to_langchain_tool(session, tool, connection=connection)
            for tool in tools
        ]
