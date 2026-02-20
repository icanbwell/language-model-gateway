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
from mcp.types import (
    LoggingMessageNotificationParams,
)
from oidcauthlib.auth.models.token import Token
from oidcauthlib.auth.token_reader import TokenReader

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from language_model_gateway.gateway.mcp.interceptors.tracing import (
    TracingMcpCallInterceptor,
)
from language_model_gateway.gateway.mcp.interceptors.truncation import (
    TruncationMcpCallInterceptor,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.logger.logging_transport import (
    LoggingTransport,
)
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)
from language_model_gateway.gateway.utilities.url_validator import URLValidator

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

    async def get_tools_by_url_async(
        self, *, tool_config: AgentConfig, headers: Dict[str, str]
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
        token: Token | None = None

        logger.info(
            f"get_tools_by_url_async called for tool: {tool_config.name}, url: {tool_config.url}, headers: {headers}"
        )

        try:
            url: str | None = tool_config.url
            if url is None:
                raise ValueError("Tool URL must be provided")

            # check the url is valid:
            url_valid, url_validation_result = URLValidator.validate(
                url=url,
                allowed_domains=self.environment_variables.mcp_tool_allowed_domains,
            )
            if not url_valid:
                raise ValueError(
                    f"Invalid URL for MCP tool: {url}. Validation result: {url_validation_result}"
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
                # replace the strings with os.path.expandvars # to allow for environment variable expansion
                mcp_tool_config["headers"] = {
                    key: os.path.expandvars(value)
                    for key, value in tool_config.headers.items()
                }

            # pass Authorization header if provided
            if headers:
                auth_headers = [
                    headers.get(key)
                    for key in headers
                    if key.lower() == "authorization"
                ]
                auth_header: str | None = auth_headers[0] if auth_headers else None
                if auth_header:
                    if tool_config.auth_providers:
                        # get the appropriate token_item for this tool
                        token_item: (
                            TokenCacheItem | None
                        ) = await self.tool_auth_manager.get_token_for_tool_async(
                            auth_header=auth_header,
                            error_message=f"No auth found for  {tool_config.name}",
                            tool_config=tool_config,
                        )
                        token = token_item.get_access_token() if token_item else None
                        if token:
                            # if we have a token_item, we need to add it to the Authorization header
                            auth_header = f"Bearer {token.token}"
                        else:
                            auth_bearer_token: str | None = TokenReader.extract_token(
                                authorization_header=auth_header
                            )
                            auth_token: Token | None = (
                                Token.create_from_token(token=auth_bearer_token)
                                if auth_bearer_token
                                and auth_bearer_token != "fake-api-key"
                                else None
                            )

                            if not auth_token and not tool_config.auth_optional:
                                raise AuthorizationMcpToolTokenInvalidException(
                                    message=f"No token found.  Authorization needed for MCP tools at {url}. "
                                    + f" for auth providers {tool_config.auth_providers}"
                                    + f", token_email: {auth_token.email if auth_token else 'None'}"
                                    + f", token_audience: {auth_token.audience if auth_token else 'None'}"
                                    + f", token_subject: {auth_token.subject if auth_token else 'None'}",
                                    tool_url=url,
                                    token=token,
                                )

                        # add the Authorization header to the mcp_tool_config headers
                        existing_headers = mcp_tool_config.get("headers") or {}
                        mcp_tool_config["headers"] = {
                            **existing_headers,
                            "Authorization": auth_header,
                        }
                    elif (
                        tool_config.auth
                    ):  # no specific auth providers are specified for the tool
                        # just pass through the current Authorization header
                        # add the Authorization header to the mcp_tool_config headers
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
            url = tool_config.url if tool_config.url else "unknown"
            first_exception1 = e.exceptions[0]
            logger.error(
                f"get_tools_by_url_async HTTP error while loading MCP tools from {url}: {type(first_exception1)} {first_exception1}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {url}. "
                + "Please provide a valid token_item in the Authorization header."
                + f" token: {token.audience if token else 'None'}",
                tool_url=url,
                token=token,
            ) from e
        except* McpToolUnauthorizedException as e:
            url = tool_config.url if tool_config.url else "unknown"
            first_exception2 = e.exceptions[0]
            logger.error(
                f"get_tools_by_url_async MCP Tool UnAuthorized error while loading MCP tools from {url}: {type(first_exception2)} {first_exception2}"
            )
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"Authorization needed for MCP tools at {url}. "
                + "Please provide a valid token in the Authorization header."
                + f" token audience: {token.audience if token else 'None'}",
                tool_url=url,
                token=token,
            ) from e
        except* Exception as e:
            url = tool_config.url if tool_config.url else "unknown"
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
                        tool_config=tool, headers=headers
                    )
                    all_tools.extend(tools_by_url)
                except* Exception as e:
                    first_exception = e.exceptions[0]
                    logger.error(
                        f"get_tools_async Failed to get tools for {tool.name} from {tool.url}: {type(first_exception)} {first_exception}"
                    )
                    raise e
        return all_tools
