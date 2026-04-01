import logging
import os
from datetime import timedelta
from typing import Dict, List

import httpx
from httpx import HTTPStatusError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool
from languagemodelcommon.configs.schemas.config_schema import AgentConfig
from languagemodelcommon.utilities.logger.logging_transport import LoggingTransport
from languagemodelcommon.utilities.token_reducer.token_reducer import TokenReducer
from mcp.types import (
    LoggingMessageNotificationParams,
    Tool as MCPTool,
)
from oidcauthlib.auth.models.token import Token

from language_model_gateway.gateway.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from language_model_gateway.gateway.mcp.interceptors.auth import (
    AuthMcpCallInterceptor,
)
from language_model_gateway.gateway.mcp.interceptors.tracing import (
    TracingMcpCallInterceptor,
)
from language_model_gateway.gateway.mcp.interceptors.truncation import (
    TruncationMcpCallInterceptor,
)
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS


# OpenTelemetry propagation for trace context

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class MCPToolProvider:
    """
    A class to provide tools for the MCP (Model Control Protocol) gateway.
    This class is responsible for managing and providing access to various tools
    that can be used in conjunction with the MCP.
    """

    def __init__(
        self,
        *,
        tool_auth_manager: ToolAuthManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        token_reducer: TokenReducer,
        truncation_interceptor: TruncationMcpCallInterceptor,
        tracing_interceptor: TracingMcpCallInterceptor,
        pass_through_token_manager: PassThroughTokenManager,
    ) -> None:
        """
        Initialize the MCPToolProvider with authentication and token management.
        Accepts:
            tool_auth_manager (ToolAuthManager): Manages tool authentication.
            environment_variables (LanguageModelGatewayEnvironmentVariables): Provides environment configuration.
            token_reducer (TokenReducer): Handles token management and reduction.
        """
        self.tool_auth_manager = tool_auth_manager
        if self.tool_auth_manager is None:
            raise ValueError("ToolAuthManager must be provided")
        if not isinstance(self.tool_auth_manager, ToolAuthManager):
            raise TypeError("auth_manager must be an instance of ToolAuthManager")

        self.environment_variables = environment_variables
        if self.environment_variables is None:
            raise ValueError("EnvironmentVariables must be provided")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "environment_variables must be an instance of EnvironmentVariables"
            )

        self.token_reducer = token_reducer
        if self.token_reducer is None:
            raise ValueError("TokenReducer must be provided")
        if not isinstance(self.token_reducer, TokenReducer):
            raise TypeError("token_reducer must be an instance of TokenReducer")

        self.truncation_interceptor = truncation_interceptor
        if self.truncation_interceptor is None:
            raise ValueError("TruncationMcpCallInterceptor must be provided")
        if not isinstance(self.truncation_interceptor, TruncationMcpCallInterceptor):
            raise TypeError(
                "truncation_interceptor must be an instance of TruncationMcpCallInterceptor"
            )

        self.tracing_interceptor = tracing_interceptor
        if self.tracing_interceptor is None:
            raise ValueError("TracingMcpCallInterceptor must be provided")
        if not isinstance(self.tracing_interceptor, TracingMcpCallInterceptor):
            raise TypeError(
                "tracing_interceptor must be an instance of TracingMcpCallInterceptor"
            )

        self.pass_through_token_manager = pass_through_token_manager
        if self.pass_through_token_manager is None:
            raise ValueError("PassThroughTokenManager must be provided")
        if not isinstance(self.pass_through_token_manager, PassThroughTokenManager):
            raise TypeError(
                "pass_through_token_manager must be an instance of PassThroughTokenManager"
            )

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
        # https://github.com/langchain-ai/langchain-mcp-adapters/blob/main/tests/test_tools.py#L387
        return httpx.AsyncClient(
            auth=auth,
            headers=headers,
            timeout=timeout,
            transport=LoggingTransport(httpx.AsyncHTTPTransport()),
        )

    @staticmethod
    async def on_mcp_tool_logging(
        params: LoggingMessageNotificationParams,
        context: CallbackContext,
    ) -> None:
        """Execute callback on logging message notification."""
        logger.info(
            f"MCP Tool Logging - Server: {context.server_name}, Level: {params.level}, Message: {params.data}"
        )

    @staticmethod
    async def on_mcp_tool_progress(
        progress: float,
        total: float | None,
        message: str | None,
        context: CallbackContext,
    ) -> None:
        logger.info(
            f"MCP Tool Progress - Server: {context.server_name}, Progress: {progress}, Total: {total}, Message: {message}"
        )

    def get_lazy_tools(
        self,
        *,
        tool_config: AgentConfig,
        headers: Dict[str, str],
        auth_interceptor: AuthMcpCallInterceptor,
    ) -> List[BaseTool]:
        """
        Create tools from static definitions without contacting the MCP server.
        When lazy_load is enabled, tool metadata comes from the config's
        tool_definitions instead of being discovered from the server.  The
        actual MCP connection is deferred to tool invocation time.
        """
        if not tool_config.tool_definitions:
            logger.warning(
                f"lazy_load is enabled for {tool_config.name} but no tool_definitions provided"
            )
            return []

        url: str | None = tool_config.url
        if url is None:
            raise ValueError(
                f"Tool URL must be provided for lazy-loaded tool: {tool_config.name}"
            )

        tool_call_timeout_seconds: int = (
            self.environment_variables.tool_call_timeout_seconds
        )
        mcp_tool_config: StreamableHttpConnection = {
            "url": url,
            "transport": "streamable_http",
            "httpx_client_factory": self.get_httpx_async_client,
            "timeout": timedelta(seconds=tool_call_timeout_seconds),
            "sse_read_timeout": timedelta(seconds=tool_call_timeout_seconds),
        }
        if tool_config.headers:
            mcp_tool_config["headers"] = {
                key: os.path.expandvars(value)
                for key, value in tool_config.headers.items()
            }

        tools: List[BaseTool] = []
        for tool_def in tool_config.tool_definitions:
            mcp_tool = MCPTool(
                name=tool_def.name,
                description=tool_def.description,
                inputSchema={"type": "object", "properties": {}},
            )
            langchain_tool = convert_mcp_tool_to_langchain_tool(
                session=None,
                tool=mcp_tool,
                connection=mcp_tool_config,
                callbacks=Callbacks(
                    on_progress=self.on_mcp_tool_progress,
                    on_logging_message=self.on_mcp_tool_logging,
                ),
                tool_interceptors=[
                    auth_interceptor.get_tool_interceptor_auth(),
                    self.tracing_interceptor.get_tool_interceptor_tracing(),
                    self.truncation_interceptor.get_tool_interceptor_truncation(),
                ],
                server_name=tool_config.name,
            )
            tools.append(langchain_tool)

        logger.info(
            f"Created {len(tools)} lazy-loaded tools for {tool_config.name}: "
            f"{[t.name for t in tools]}"
        )
        return tools

    async def get_tools_by_url_async(
        self,
        *,
        tool_config: AgentConfig,
        headers: Dict[str, str],
        auth_interceptor: AuthMcpCallInterceptor,
    ) -> List[BaseTool]:
        """
        Get tools by their MCP URL asynchronously.
        This method retrieves tools from the MCP based on the provided URL and headers.
        Args:
            tool_config: An AgentConfig instance containing the tool's configuration.
            headers: A dictionary of headers to include in the request, such as Authorization.
        Returns:
            A list of BaseTool instances retrieved from the MCP.
        """
        if tool_config.lazy_load:
            return self.get_lazy_tools(
                tool_config=tool_config,
                headers=headers,
                auth_interceptor=auth_interceptor,
            )

        token: Token | None = None

        safe_header_keys = [k for k in headers.keys()] if headers else []
        logger.info(
            f"get_tools_by_url_async called for tool: {tool_config.name}, url: {tool_config.url}, header_keys: {safe_header_keys}"
        )

        try:
            url: str | None = tool_config.url
            if url is None:
                raise ValueError("Tool URL must be provided")

            tool_call_timeout_seconds: int = (
                self.environment_variables.tool_call_timeout_seconds
            )

            mcp_tool_config: StreamableHttpConnection = {
                "url": url,
                "transport": "streamable_http",
                "httpx_client_factory": self.get_httpx_async_client,
                "timeout": timedelta(seconds=tool_call_timeout_seconds),
                "sse_read_timeout": timedelta(seconds=tool_call_timeout_seconds),
            }
            if tool_config.headers:
                # replace the strings with os.path.expandvars # to allow for environment variable expansion
                mcp_tool_config["headers"] = {
                    key: os.path.expandvars(value)
                    for key, value in tool_config.headers.items()
                }

            # Attach an Authorization header for tool discovery so that
            # MCP servers requiring auth can respond to tools/list.
            # - Tools with auth_providers: resolve via token exchange
            #   (same logic used at invocation time).
            # - Tools with auth but no specific auth_providers: pass
            #   through the caller's raw Authorization header.
            if headers and tool_config.auth:
                if tool_config.auth_providers:
                    resolved_header: (
                        str | None
                    ) = await auth_interceptor.resolve_auth_header_for_discovery(
                        tool_config
                    )
                    if resolved_header:
                        existing_headers = mcp_tool_config.get("headers") or {}
                        mcp_tool_config["headers"] = {
                            **existing_headers,
                            "Authorization": resolved_header,
                        }
                else:
                    auth_headers = [
                        headers.get(key)
                        for key in headers
                        if key.lower() == "authorization"
                    ]
                    auth_header: str | None = auth_headers[0] if auth_headers else None
                    if auth_header:
                        existing_headers = mcp_tool_config.get("headers") or {}
                        mcp_tool_config["headers"] = {
                            **existing_headers,
                            "Authorization": auth_header,
                        }

            tool_names: List[str] | None = (
                tool_config.tools.split(",") if tool_config.tools else None
            )

            client: MultiServerMCPClient = MultiServerMCPClient(
                connections={
                    f"{tool_config.name}": mcp_tool_config,
                },
                callbacks=Callbacks(
                    on_progress=self.on_mcp_tool_progress,
                    on_logging_message=self.on_mcp_tool_logging,
                ),
                tool_interceptors=[  # First interceptor in list becomes outermost layer.
                    auth_interceptor.get_tool_interceptor_auth(),
                    self.tracing_interceptor.get_tool_interceptor_tracing(),
                    self.truncation_interceptor.get_tool_interceptor_truncation(),
                ],
            )
            tools: List[BaseTool] = await client.get_tools()
            if tool_names and tools:
                # filter tools by tool_name if provided
                tools = [t for t in tools if t.name in tool_names]
            return tools
        except* HTTPStatusError as e:
            tool_url: str = tool_config.url if tool_config.url else "unknown"
            first_exception1 = e.exceptions[0]
            logger.error(
                f"get_tools_by_url_async HTTP error while loading MCP tools from {tool_url}: {type(first_exception1)} {first_exception1}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {tool_url}. "
                + "Please provide a valid token_item in the Authorization header."
                + f" token: {token.audience if token else 'None'}",
                tool_url=tool_url,
                token=token,
            ) from e
        except* McpToolUnauthorizedException as e:
            tool_url = tool_config.url if tool_config.url else "unknown"
            first_exception2 = e.exceptions[0]
            logger.error(
                f"get_tools_by_url_async MCP Tool UnAuthorized error while loading MCP tools from {tool_url}: {type(first_exception2)} {first_exception2}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {tool_url}. "
                + "Please provide a valid token in the Authorization header."
                + f" token audience: {token.audience if token else 'None'}",
                tool_url=tool_url,
                token=token,
            ) from e
        except* Exception as e:
            tool_url = tool_config.url if tool_config.url else "unknown"
            logger.error(
                f"get_tools_by_url_async Failed to load MCP tools from {tool_url}: {type(e.exceptions[0])} {e}"
            )
            raise e

    async def get_tools_async(
        self,
        *,
        tools: list[AgentConfig],
        headers: Dict[str, str],
        auth_interceptor: AuthMcpCallInterceptor,
    ) -> list[BaseTool]:
        # get list of tools from the tools from each agent and then concatenate them
        all_tools: List[BaseTool] = []
        for tool in tools:
            if tool.url is not None:
                try:
                    tools_by_url: List[BaseTool] = await self.get_tools_by_url_async(
                        tool_config=tool,
                        headers=headers,
                        auth_interceptor=auth_interceptor,
                    )
                    all_tools.extend(tools_by_url)
                except* AuthorizationMcpToolTokenInvalidException as auth_eg:
                    auth_exception = auth_eg.exceptions[0]
                    logger.error(
                        f"get_tools_async Authorization error for {tool.name} from {tool.url}: {type(auth_exception)} {auth_exception}"
                    )
                    raise auth_eg
                except* Exception as conn_eg:
                    conn_exception = conn_eg.exceptions[0]
                    if tool.auth == "jwt_token" and not tool.auth_optional:
                        logger.error(
                            f"get_tools_async Failed to connect to auth-required MCP server for {tool.name} at {tool.url}, "
                            f"raising error: {type(conn_exception).__name__}: {conn_exception}"
                        )
                        raise conn_eg
                    logger.warning(
                        f"get_tools_async Failed to connect to MCP server for {tool.name} at {tool.url}, "
                        f"skipping tool: {type(conn_exception).__name__}: {conn_exception}"
                    )
        return all_tools
