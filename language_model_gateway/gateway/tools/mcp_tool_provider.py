import httpx
import logging
import os
from typing import Dict, List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.sessions import StreamableHttpConnection

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.langchain_overrides.multiserver_mcp_client_with_caching import (
    MultiServerMCPClientWithCaching,
)
from language_model_gateway.gateway.utilities.cache.mcp_tools_expiring_cache import (
    McpToolsMetadataExpiringCache,
)
from language_model_gateway.gateway.utilities.logger.logging_transport import (
    LoggingTransport,
)

logger = logging.getLogger(__name__)


class MCPToolProvider:
    """
    A class to provide tools for the MCP (Model Control Protocol) gateway.
    This class is responsible for managing and providing access to various tools
    that can be used in conjunction with the MCP.
    """

    def __init__(
        self,
        *,
        cache: McpToolsMetadataExpiringCache,
        token_exchange_manager: TokenExchangeManager,
    ) -> None:
        """
        Initialize the MCPToolProvider with a cache.

        Args:
            cache: An ExpiringCache instance to store tools by their MCP URLs.
        """
        self.tools_by_mcp_url: Dict[str, List[BaseTool]] = {}
        self._cache: McpToolsMetadataExpiringCache = cache
        assert self._cache is not None, "Cache must be provided"

        self.token_exchange_manager: TokenExchangeManager = token_exchange_manager
        assert self.token_exchange_manager is not None, (
            "MCPToolProvider requires a TokenExchangeManager instance."
        )
        assert isinstance(self.token_exchange_manager, TokenExchangeManager)

    async def load_async(self) -> None:
        pass

    @staticmethod
    def get_httpx_async_client(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        """
        Get an async HTTP client for making requests to MCP tools.

        Returns:
            An instance of httpx.AsyncClient configured for MCP tool requests.
        """
        return httpx.AsyncClient(
            auth=auth,
            headers=headers,
            timeout=timeout,
            transport=LoggingTransport(httpx.AsyncHTTPTransport()),
        )

    async def get_tools_by_url_async(
        self, *, tool: AgentConfig, headers: Dict[str, str]
    ) -> List[BaseTool]:
        try:
            url: str | None = tool.url
            assert url is not None, "Tool URL must be provided"
            # first see if the url is already loaded
            if url in self.tools_by_mcp_url:
                return self.tools_by_mcp_url[url]

            mcp_tool_config: StreamableHttpConnection = {
                "url": url,
                "transport": "streamable_http",
                "httpx_client_factory": self.get_httpx_async_client,
            }
            if tool.headers:
                # replace the strings with os.path.expandvars # to allow for environment variable expansion
                mcp_tool_config["headers"] = {
                    key: os.path.expandvars(value)
                    for key, value in tool.headers.items()
                }

            # pass Authorization header if provided
            if headers:
                auth_header: str | None = next(
                    (
                        headers.get(key)
                        for key in headers
                        if key.lower() == "authorization"
                    ),
                    None,
                )
                if auth_header:
                    # get the appropriate token for this tool
                    token: (
                        str | None
                    ) = await self.token_exchange_manager.get_token_for_tool(
                        auth_header=auth_header,
                        error_message="",
                        tool_name=tool.name,
                        tool_auth_audiences=tool.auth_audiences,
                    )
                    if token:
                        # if we have a token, we need to add it to the Authorization header
                        auth_header = f"Bearer {token}"
                    # add the Authorization header to the mcp_tool_config headers
                    mcp_tool_config["headers"] = {
                        **mcp_tool_config.get("headers", {}),
                        "Authorization": auth_header,
                    }
                logger.debug(
                    f"Loading MCP tools with Authorization header: {auth_header}"
                )

            tool_names: List[str] | None = tool.tools.split(",") if tool.tools else None
            client: MultiServerMCPClientWithCaching = MultiServerMCPClientWithCaching(
                cache=self._cache,
                connections={
                    f"{tool.name}": mcp_tool_config,
                },
                tool_names=tool_names,
            )
            tools: List[BaseTool] = await client.get_tools()
            if tool_names and tools:
                # filter tools by tool_name if provided
                tools = [t for t in tools if t.name in tool_names]
            self.tools_by_mcp_url[url] = tools
            return tools
        except* Exception as e:
            url = tool.url if tool.url else "unknown"
            logger.error(
                f"get_tools_by_url_async Failed to load MCP tools from {url}: {type(e)} {e}"
            )
            raise e

    async def get_tools_async(
        self, *, tools: list[AgentConfig], headers: Dict[str, str]
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
                except* Exception as e:
                    logger.error(
                        f"get_tools_async Failed to get tools for {tool.name} from {tool.url}: {type(e)} {e}"
                    )
                    raise e
        return all_tools
