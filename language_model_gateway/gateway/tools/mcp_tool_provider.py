import httpx
import logging
import os
from typing import Dict, List

from httpx import HTTPStatusError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.sessions import StreamableHttpConnection

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from language_model_gateway.gateway.auth.models.token import Token
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_reader import TokenReader
from language_model_gateway.gateway.langchain_overrides.multiserver_mcp_client_with_caching import (
    MultiServerMCPClientWithCaching,
)
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
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
        auth_manager: AuthManager,
    ) -> None:
        """
        Initialize the MCPToolProvider with a cache.

        Args:
            cache: An ExpiringCache instance to store tools by their MCP URLs.
        """
        self.tools_by_mcp_url: Dict[str, List[BaseTool]] = {}
        self._cache: McpToolsMetadataExpiringCache = cache
        assert self._cache is not None, "Cache must be provided"

        self.auth_manager = auth_manager
        assert self.auth_manager is not None, "AuthManager must be provided"
        assert isinstance(self.auth_manager, AuthManager)

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
        """
        Get tools by their MCP URL asynchronously.
        This method retrieves tools from the MCP based on the provided URL and headers.
        Args:
            tool: An AgentConfig instance containing the tool's configuration.
            headers: A dictionary of headers to include in the request, such as Authorization.
        Returns:
            A list of BaseTool instances retrieved from the MCP.
        """
        token: Token | None = None

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
                if auth_header and tool.auth_providers:
                    # get the appropriate token_item for this tool
                    token_item: (
                        TokenCacheItem | None
                    ) = await self.auth_manager.get_token_for_tool_async(
                        auth_header=auth_header,
                        error_message="",
                        tool_name=tool.name,
                        tool_auth_providers=tool.auth_providers,
                    )
                    token = token_item.get_token() if token_item else None
                    if token:
                        # if we have a token_item, we need to add it to the Authorization header
                        auth_header = f"Bearer {token.token}"
                    else:
                        auth_bearer_token: str | None = TokenReader.extract_token(
                            authorization_header=auth_header
                        )
                        auth_token: Token | None = Token.create(token=auth_bearer_token)
                        raise AuthorizationMcpToolTokenInvalidException(
                            message=f"No token found.  Authorization needed for MCP tools at {url}. "
                            + f" for auth providers {tool.auth_providers}"
                            + f", token_email: {auth_token.email if auth_token else 'None'}"
                            + f", token_audience: {auth_token.audience if auth_token else 'None'}"
                            + f", token_subject: {auth_token.subject if auth_token else 'None'}",
                            tool_url=url,
                            token=token,
                        )

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
        except* HTTPStatusError as e:
            url = tool.url if tool.url else "unknown"
            logger.error(
                f"get_tools_by_url_async HTTP error while loading MCP tools from {url}: {type(e)} {e}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {url}. "
                + "Please provide a valid token_item in the Authorization header."
                + f" token: {token.audience if token else 'None'}",
                tool_url=url,
                token=token,
            ) from e
        except* McpToolUnauthorizedException as e:
            url = tool.url if tool.url else "unknown"
            logger.error(
                f"get_tools_by_url_async HTTP error while loading MCP tools from {url}: {type(e)} {e}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {url}. "
                + "Please provide a valid token_item in the Authorization header."
                + f" token: {token.audience if token else 'None'}",
                tool_url=url,
                token=token,
            ) from e
        except* Exception as e:
            url = tool.url if tool.url else "unknown"
            logger.error(
                f"get_tools_by_url_async Failed to load MCP tools from {url}: {type(e.exceptions[0])} {e}"
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
