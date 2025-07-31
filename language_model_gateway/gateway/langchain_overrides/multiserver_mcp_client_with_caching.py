import asyncio
import logging
from typing import override, List, Dict
from uuid import UUID, uuid4

from httpx import HTTPStatusError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection
from langchain_mcp_adapters.sessions import create_session

# noinspection PyProtectedMember
from langchain_mcp_adapters.tools import (
    _list_all_tools,
    convert_mcp_tool_to_langchain_tool,
)
from mcp import ClientSession, Tool

from language_model_gateway.gateway.utilities.cache.mcp_tools_expiring_cache import (
    McpToolsMetadataExpiringCache,
)

logger = logging.getLogger(__name__)


class MultiServerMCPClientWithCaching(MultiServerMCPClient):  # type: ignore[misc]
    """A MultiServerMCPClient that caches tool metadata to avoid repeated calls to the MCP server.

    This class extends the MultiServerMCPClient to cache the metadata of tools
    across multiple calls to `get_tools`. It allows for efficient retrieval of tools
    without needing to repeatedly query the MCP server for the same tool metadata.
    """

    _identifier: UUID = uuid4()
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(
        self,
        *,
        connections: dict[str, Connection] | None = None,
        cache: McpToolsMetadataExpiringCache,
        tool_names: List[str] | None,
    ) -> None:
        """
        Initialize the async config reader

        Args:
            cache: Expiring cache for model configurations
        """
        assert cache is not None
        self._cache: McpToolsMetadataExpiringCache = cache
        assert self._cache is not None
        self._tool_names: List[str] | None = tool_names
        super().__init__(connections=connections)

    async def load_tools_metadata_cache(
        self, *, server_name: str | None = None, tool_names: List[str] | None
    ) -> None:
        """Get a list of all tools from all connected servers.

        Args:
            server_name: Optional name of the server to get tools from.
                If None, all tools from all servers will be returned (default).
            tool_names: Optional list of tool names to filter the tools.

        NOTE: a new session will be created for each tool call

        Returns:
            A list of LangChain tools

        """
        async with self._lock:
            cache: Dict[str, List[Tool]] | None = await self._cache.get()
            assert cache is not None

            if server_name is not None:
                if server_name not in self.connections:
                    msg = f"Couldn't find a server with name '{server_name}', expected one of '{list(self.connections.keys())}'"
                    raise ValueError(msg)
                connection_for_server = self.connections[server_name]
                if connection_for_server["url"] not in cache:
                    cache[
                        connection_for_server["url"]
                    ] = await self.load_metadata_for_mcp_tools(
                        session=None,
                        connection=connection_for_server,
                        tool_names=tool_names,
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
                    if connection["url"] not in cache:
                        cache[
                            connection["url"]
                        ] = await self.load_metadata_for_mcp_tools(
                            session=None,
                            connection=connection,
                            tool_names=self._tool_names,
                        )
                        logger.info(f"Loaded tools for connection {connection['url']}")
                    else:
                        # see if we are missing any tools in the cache
                        if self._tool_names:
                            cached_tool_names = [
                                tool.name for tool in cache[connection["url"]]
                            ]
                            missing_tools = set(self._tool_names) - set(
                                cached_tool_names
                            )
                            if missing_tools:
                                logger.info(
                                    f"Missing tools {missing_tools} for connection {connection['url']}, loading them"
                                )
                                tools = await self.load_metadata_for_mcp_tools(
                                    session=None,
                                    connection=connection,
                                    tool_names=list(missing_tools),
                                )
                                cache[connection["url"]].extend(tools)
                            else:
                                logger.debug(
                                    f"Tools for connection {connection['url']} are already cached and all tools are present"
                                )
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

        await self.load_tools_metadata_cache(
            server_name=server_name, tool_names=self._tool_names
        )

        async with self._lock:
            cache: Dict[str, List[Tool]] | None = await self._cache.get()
            assert cache is not None, "Cache must be initialized before getting tools"

            # create LangChain tools from the loaded MCP tools
            all_tools: List[BaseTool] = []
            for connection in self.connections.values():
                tools_for_connection = cache[connection["url"]]
                all_tools.extend(
                    self.create_tools_from_list(
                        tools=tools_for_connection, session=None, connection=connection
                    )
                )
            return all_tools

    @staticmethod
    async def load_metadata_for_mcp_tools(
        *,
        session: ClientSession | None,
        connection: Connection | None = None,
        tool_names: List[str] | None,
    ) -> list[Tool]:
        """Load all available MCP tools and convert them to LangChain tools.

        Args:
            session: The MCP client session. If None, connection must be provided.
            connection: Connection config to create a new session if session is None.
            tool_names: Optional list of tool names to filter the tools.
                If None, all tools will be returned.

        Returns:
            List of LangChain tools. Tool annotations are returned as part
            of the tool metadata object.

        Raises:
            ValueError: If neither session nor connection is provided.
        """
        if session is None and connection is None:
            msg = "Either a session or a connection config must be provided"
            raise ValueError(msg)

        tools: List[Tool]
        try:
            if session is None:
                # If a session is not provided, we will create one on the fly
                async with create_session(connection) as tool_session:
                    await tool_session.initialize()
                    tools = await _list_all_tools(tool_session)
            else:
                tools = await _list_all_tools(session)
        except* HTTPStatusError as exc:
            # if there is
            # exc is a ExceptionGroup, so we can catch it with a wildcard
            # and log the type of the exception
            # if there is just one exception then check if it is 401 and then return a custom error
            if len(exc.exceptions) == 1 and isinstance(
                exc.exceptions[0], HTTPStatusError
            ):
                http_status_exception: HTTPStatusError = exc.exceptions[0]

                if http_status_exception.response.status_code == 401:
                    logger.error(
                        f"load_metadata_for_mcp_tools Unauthorized access to MCP tools: {http_status_exception}"
                    )
                    raise ValueError(
                        f"Not allowed to access MCP tool at {http_status_exception.request.url}. Perhaps your login token has expired. Please reload to login again."
                    ) from exc
            logger.error(
                f"load_metadata_for_mcp_tools Failed to load MCP tools: {type(exc)}"
            )
        except* Exception as e:
            url: str = connection.get("url") if connection else "unknown"
            logger.error(
                f"load_metadata_for_mcp_tools Failed to load MCP tools from {url}: {type(e)} {e}"
            )
            raise e

        if tool_names is not None:
            # Filter tools by names if provided
            tools = [tool for tool in tools if tool.name in tool_names]
        return tools

    @staticmethod
    def create_tools_from_list(
        *,
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
        try:
            return [
                convert_mcp_tool_to_langchain_tool(session, tool, connection=connection)
                for tool in tools
            ]
        except Exception as e:
            url: str = connection.get("url") if connection else "unknown"
            logger.error(
                f"Failed to convert MCP tools to LangChain tools from {url},  tools={[t.name for t in tools]}: {e}"
            )
            raise e
