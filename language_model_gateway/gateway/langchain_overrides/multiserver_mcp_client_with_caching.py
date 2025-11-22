import asyncio
import logging
from typing import override, List, Dict, Any, cast, Optional
from uuid import UUID, uuid4

from httpx import HTTPStatusError, ConnectError, Headers
from langchain_core.tools import BaseTool, ToolException
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection, StreamableHttpConnection
from langchain_mcp_adapters.sessions import create_session

# noinspection PyProtectedMember
from langchain_mcp_adapters.tools import (
    _list_all_tools,
    NonTextContent,
    _convert_call_tool_result,
)
from mcp import ClientSession, Tool

from language_model_gateway.gateway.langchain_overrides.structured_tool_with_output_limits import (
    StructuredToolWithOutputLimits,
)
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_not_found_exception import (
    McpToolNotFoundException,
)
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unknown_exception import (
    McpToolUnknownException,
)
from language_model_gateway.gateway.utilities.cache.mcp_tools_expiring_cache import (
    McpToolsMetadataExpiringCache,
)
from mcp.types import Tool as MCPTool

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class MultiServerMCPClientWithCaching(MultiServerMCPClient):
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
        connections: Optional[dict[str, Connection]] = None,
        cache: McpToolsMetadataExpiringCache,
        tool_names: List[str] | None,
        tool_output_token_limit: int | None,
        token_reducer: TokenReducer,
    ) -> None:
        """
        Initialize the async config reader

        Args:
            cache: Expiring cache for model configurations
            connections: Optional dictionary of server name to connection config.
                If None, an empty dictionary will be used (default).
            tool_names: Optional list of tool names to filter the tools.
                If None, all tools will be returned.
            tool_output_token_limit: Optional limit for the number of tokens
            token_reducer: TokenReducer instance to manage token limits
        """
        if cache is None:
            raise ValueError("cache must not be None")
        self._cache: McpToolsMetadataExpiringCache = cache
        self._tool_names: List[str] | None = tool_names
        self._tool_output_token_limit: int | None = tool_output_token_limit
        if not isinstance(self._cache, McpToolsMetadataExpiringCache):
            raise TypeError(
                f"self._cache must be McpToolsMetadataExpiringCache, got {type(self._cache)}"
            )
        if not isinstance(token_reducer, TokenReducer):
            raise TypeError(
                f"token_reducer must be TokenReducer, got {type(token_reducer)}"
            )
        self.token_reducer = token_reducer
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
            if cache is None:
                cache = await self._cache.create()
                if cache is None:
                    raise RuntimeError("Cache must be initialized before getting tools")

            if server_name is not None:
                if server_name not in self.connections:
                    msg = f"Couldn't find a server with name '{server_name}', expected one of '{list(self.connections.keys())}'"
                    raise ValueError(msg)
                connection_for_server: StreamableHttpConnection = cast(
                    StreamableHttpConnection, self.connections[server_name]
                )
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
                connection: StreamableHttpConnection
                for connection in [
                    cast(StreamableHttpConnection, c) for c in self.connections.values()
                ]:
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
            # set the cache with the loaded tools
            await self._cache.set(cache)

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
            if cache is None:
                raise RuntimeError("Cache must be initialized before getting tools")

            # create LangChain tools from the loaded MCP tools
            all_tools: List[BaseTool] = []
            connection: StreamableHttpConnection
            for connection in [
                cast(StreamableHttpConnection, c) for c in self.connections.values()
            ]:
                tools_for_connection: List[Tool] = cache[connection["url"]]
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
        connection: Optional[Connection] = None,
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
            if session is None and connection is not None:
                # If a session is not provided, we will create one on the fly
                async with create_session(connection) as tool_session:
                    await tool_session.initialize()
                    tools = await _list_all_tools(tool_session)
            elif session is not None:
                tools = await _list_all_tools(session)
            else:
                msg = "Either a session or a connection config must be provided"
                raise ValueError(msg)
        except* HTTPStatusError as exc:
            # if there is
            # exc is a ExceptionGroup, so we can catch it with a wildcard
            # and log the type of the exception
            # if there is just one exception then check if it is 401 and then return a custom error
            if len(exc.exceptions) >= 1 and isinstance(
                exc.exceptions[0], HTTPStatusError
            ):
                http_status_exception: HTTPStatusError = exc.exceptions[0]
                response_text: str | None
                # Read response text before the stream is closed
                if not http_status_exception.response.is_closed:
                    response_bytes: bytes = await http_status_exception.response.aread()
                    response_text = response_bytes.decode()
                else:
                    response_text = http_status_exception.response.reason_phrase
                # Handle 401 error
                if http_status_exception.response.status_code == 401:
                    authorization_header = http_status_exception.request.headers.get(
                        "authorization"
                    )
                    # see if the response as a www-authenticate header
                    www_authenticate_header = (
                        http_status_exception.response.headers.get("www-authenticate")
                    )

                    message = (
                        f"Not allowed to access MCP tool at {http_status_exception.request.url}."
                        + (
                            " Perhaps your login token has expired. Please reload to login again."
                            if authorization_header
                            else "No authorization header was provided in the request."
                        )
                        + f" Response: {response_text}"
                        + (
                            f" WWW-Authenticate header: {www_authenticate_header}"
                            if www_authenticate_header
                            else ""
                        )
                    )
                    logger.error(
                        f"load_metadata_for_mcp_tools Unauthorized access to MCP tools: {http_status_exception}"
                        f": {message}"
                        f" Response: {response_text}"
                        f" Headers: {http_status_exception.request.headers}"
                        f" Authorization: {authorization_header}"
                    )

                    raise McpToolUnauthorizedException(
                        message=message,
                        status_code=http_status_exception.response.status_code,
                        headers=http_status_exception.response.headers,
                        url=str(http_status_exception.request.url),
                    ) from exc
                elif http_status_exception.response.status_code == 404:
                    raise McpToolNotFoundException(
                        message=f"MCP tool not found at {http_status_exception.request.url}. "
                        + "Please check the URL and try again."
                        + f" Response: {response_text}",
                        status_code=http_status_exception.response.status_code,
                        headers=http_status_exception.response.headers,
                        url=str(http_status_exception.request.url),
                    ) from exc
                else:
                    raise McpToolUnknownException(
                        message=f"Error accessing MCP tool at {http_status_exception.request.url}. "
                        + f"Response: {response_text}",
                        status_code=http_status_exception.response.status_code,
                        headers=http_status_exception.response.headers,
                        url=str(http_status_exception.request.url),
                    ) from exc
            else:
                logger.error(
                    f"load_metadata_for_mcp_tools Received error when loading MCP tools: {type(exc)}"
                )
                raise
        except* ConnectError as exc:
            if len(exc.exceptions) == 1 and isinstance(exc.exceptions[0], ConnectError):
                # If there is just one exception, we can log it directly
                http_connect_exception: ConnectError = exc.exceptions[0]
                # Handle connection errors
                logger.error(
                    f"load_metadata_for_mcp_tools Failed to connect to MCP server: {type(http_connect_exception)} {http_connect_exception}"
                )
                raise ConnectionError(
                    f"Failed to connect to the MCP server: {http_connect_exception.request.url}. Please check your connection."
                ) from http_connect_exception
            else:
                raise
        except* Exception as exc:
            url: str = cast(str, connection.get("url")) if connection else "unknown"
            if len(exc.exceptions) >= 1:
                first_exception: Exception = exc.exceptions[0]
                logger.error(
                    f"load_metadata_for_mcp_tools Failed to load MCP tools from {url}: {type(first_exception)} {first_exception}"
                )
            raise McpToolUnknownException(
                message=f"Error accessing MCP tool at {url}. ",
                status_code=None,
                headers=None,
                url=url,
            ) from exc

        if tool_names is not None:
            # Filter tools by names if provided
            tools = [tool for tool in tools if tool.name in tool_names]
        return tools

    @staticmethod
    def convert_mcp_tool_to_langchain_tool(
        session: ClientSession | None,
        tool: MCPTool,
        *,
        connection: Optional[Connection] = None,
        tool_output_token_limit: int | None,
        token_reducer: TokenReducer,
    ) -> BaseTool:
        """Convert an MCP tool to a LangChain tool.

        NOTE: this tool can be executed only in a context of an active MCP client session.

        Args:
            session: MCP client session
            tool: MCP tool to convert
            connection: Optional connection config to use to create a new session
                        if a `session` is not provided
            tool_output_token_limit: Optional limit for the number of tokens
            token_reducer: token reducer that can reduce the number of tokens

        Returns:
            a LangChain tool

        """
        if session is None and connection is None:
            msg = "Either a session or a connection config must be provided"
            raise ValueError(msg)

        async def call_tool(
            **arguments: dict[str, Any],
        ) -> tuple[str | list[str], list[NonTextContent] | None]:
            if session is None and connection is not None:
                # If a session is not provided, we will create one on the fly
                async with create_session(connection) as tool_session:
                    await tool_session.initialize()
                    call_tool_result = await tool_session.call_tool(
                        tool.name,
                        arguments,
                    )
            elif session is not None:
                call_tool_result = await session.call_tool(tool.name, arguments)
            else:
                raise ValueError(
                    "Either a session or a connection config must be provided"
                )
            try:
                return _convert_call_tool_result(call_tool_result)
            except ToolException as e:
                http_connection: StreamableHttpConnection | None = (
                    cast(StreamableHttpConnection, connection) if connection else None
                )
                headers_dict = (
                    http_connection.get("headers") if http_connection else None
                )
                headers_obj = (
                    Headers(headers_dict) if headers_dict is not None else None
                )
                raise McpToolUnknownException(
                    message=(
                        f"Unknown Error calling MCP tool '{tool.name}'\n"
                        f"Headers: {dict(headers_obj) if headers_obj is not None else 'None'}"
                    ),
                    status_code=0,
                    headers=headers_obj,
                    url=(http_connection.get("url") or "unknown")
                    if http_connection
                    else "unknown",
                ) from e

        return StructuredToolWithOutputLimits(
            name=tool.name,
            description=tool.description or "",
            args_schema=tool.inputSchema,
            coroutine=call_tool,
            response_format="content_and_artifact",
            metadata=tool.annotations.model_dump() if tool.annotations else None,
            limit_output_tokens=tool_output_token_limit,
            token_reducer=token_reducer,
        )

    def create_tools_from_list(
        self,
        *,
        tools: list[Tool],
        session: ClientSession | None = None,
        connection: Optional[Connection] = None,
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
                self.convert_mcp_tool_to_langchain_tool(
                    session,
                    tool,
                    connection=connection,
                    tool_output_token_limit=self._tool_output_token_limit,
                    token_reducer=self.token_reducer,
                )
                for tool in tools
            ]
        except Exception as e:
            url: str = cast(str, connection.get("url")) if connection else "unknown"
            logger.error(
                f"Failed to convert MCP tools to LangChain tools from {url},  tools={[t.name for t in tools]}: {e}"
            )
            raise e
