import logging
import os
from logging import DEBUG
from typing import Dict, List, Callable, Awaitable, Any
import json

import httpx
from datetime import timedelta
from httpx import HTTPStatusError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
    ToolCallInterceptor,
)
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from mcp.types import (
    ContentBlock,
    TextContent,
    LoggingMessageNotificationParams,
    EmbeddedResource,
    TextResourceContents,
    CallToolResult,
)
from oidcauthlib.auth.models.token import Token
from oidcauthlib.auth.token_reader import TokenReader

# OpenTelemetry propagation for trace context
from opentelemetry.propagate import inject
from opentelemetry.trace import get_tracer, SpanKind

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
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

    def get_tool_interceptor_truncation(self) -> ToolCallInterceptor:
        """
        Get an interceptor to truncate tool output based on token limits.
        """

        async def tool_interceptor_truncation(
            request: MCPToolCallRequest,
            handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
        ) -> MCPToolCallResult:
            """
            Interceptor to truncate tool output based on token limits.
            This interceptor checks if the tool has a specified output token limit
            and truncates the output accordingly using a TokenReducer.

            Args:
                request: The MCPToolCallRequest containing tool call details.
                handler: The next handler in the interceptor chain.

            Returns:
                An MCPToolCallResult with potentially truncated output.
            """
            result: MCPToolCallResult = await handler(request)
            if isinstance(result, CallToolResult):
                if logger.isEnabledFor(DEBUG):
                    # See if there is structured_content
                    structured_content: dict[str, Any] | None = result.structuredContent
                    logger.debug(
                        f"=== Tool structured output received: {type(structured_content)}: {structured_content} ==="
                    )
                    logger.debug(
                        f"=== Received tool output before truncation {len(result.content)} blocks ==="
                    )
                    content_block: ContentBlock
                    for content_index, content_block in enumerate(result.content):
                        if isinstance(content_block, TextContent):
                            logger.debug(
                                f"Content Block [{content_index}] {content_block.text}"
                            )
                    logger.debug(
                        f"=== End of tool output before truncation {len(result.content)} blocks ==="
                    )

                max_token_limit: int = (
                    self.environment_variables.tool_output_token_limit or -1
                )
                tokens_limit_left: int = max_token_limit

                content_block_list: List[ContentBlock] = []
                content_block1: ContentBlock
                for content_block1 in result.content:
                    # If there's a positive limit and we've exhausted it, stop processing further blocks
                    if max_token_limit > 0 and tokens_limit_left <= 0:
                        break

                    if isinstance(content_block1, TextContent):
                        text: str = content_block1.text
                        token_count: int = self.token_reducer.count_tokens(text=text)

                        if max_token_limit > 0 and token_count > tokens_limit_left:
                            # Truncate to the remaining budget and re-count using the truncated text
                            truncated_text = self.token_reducer.reduce_tokens(
                                text=text,
                                max_tokens=tokens_limit_left,
                                preserve_start=0,
                            )
                            truncated_count: int = self.token_reducer.count_tokens(
                                text=truncated_text
                            )
                            logger.debug(
                                f"Truncated text:\nOriginal:{text}\nTruncated:{truncated_text}\nOriginal tokens:{token_count}, Truncated tokens:{truncated_count}, Remaining before:{tokens_limit_left}"
                            )

                            # Only append if truncation produced some tokens
                            if truncated_count > 0:
                                content_block1.text = truncated_text
                                content_block_list.append(content_block1)
                                tokens_limit_left -= truncated_count
                            # If budget exhausted (or zero-length), stop
                            if max_token_limit > 0 and tokens_limit_left <= 0:
                                tokens_limit_left = 0
                                break
                        else:
                            # No truncation needed (or no limit in effect)
                            content_block_list.append(content_block1)
                            if max_token_limit > 0:
                                tokens_limit_left -= token_count
                                if tokens_limit_left <= 0:
                                    tokens_limit_left = 0
                                    # Budget met exactly/exhausted after this block
                                    break
                    else:
                        # Preserve non-text content blocks unchanged
                        content_block_list.append(content_block1)

                if logger.isEnabledFor(DEBUG):
                    logger.debug(
                        f"===== Returning tool output after truncation {len(content_block_list)} blocks ====="
                    )
                    for content_index, content_block in enumerate(content_block_list):
                        if isinstance(content_block, TextContent):
                            logger.debug(
                                f"[{content_index}] TextContent: {content_block.text}"
                            )
                        elif isinstance(content_block, EmbeddedResource):
                            if isinstance(content_block.resource, TextResourceContents):
                                logger.debug(
                                    f"[{content_index}] EmbeddedResource: {content_block.resource.text}"
                                )
                    logger.debug(
                        f"===== End of tool output after truncation {len(content_block_list)} blocks ====="
                    )

                # now set this as the new result content
                result.content = content_block_list
            return result

        return tool_interceptor_truncation

    def get_tool_interceptor_tracing(self) -> ToolCallInterceptor:
        """
        Interceptor that wraps each MCP tool call in an OpenTelemetry span.
        Captures useful attributes and marks errors on exceptions.
        """

        tracer = get_tracer(__name__)

        async def tool_interceptor_tracing(
            request: MCPToolCallRequest,
            handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
        ) -> MCPToolCallResult:
            span_name = f"mcp.tool.{getattr(request, 'tool_name', 'call')}"
            # Start span as current so downstream HTTP client propagation uses the active context
            with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                # Add common attributes for filtering/analysis
                try:
                    span.set_attribute(
                        "mcp.server_name", getattr(request, "server_name", "unknown")
                    )
                    span.set_attribute(
                        "mcp.tool_name", getattr(request, "tool_name", "unknown")
                    )
                    # Serialize complex arguments into JSON string to satisfy OTEL attribute type requirements
                    args_val: Any = getattr(request, "arguments", {})
                    try:
                        args_str = json.dumps(args_val, ensure_ascii=False)
                    except Exception:
                        args_str = str(args_val)
                    span.set_attribute("mcp.arguments", args_str)
                except Exception:
                    # defensive: attribute setting should not break the call
                    pass
                try:
                    result = await handler(request)
                    # Optionally record result metadata size
                    try:
                        if isinstance(result, CallToolResult):
                            span.set_attribute(
                                "mcp.result.content_blocks", len(result.content)
                            )
                            if result.structuredContent is not None:
                                span.set_attribute("mcp.result.structured", True)
                    except Exception:
                        pass
                    return result
                except Exception as err:
                    # Record exception on span, mark status error, then re-raise
                    try:
                        span.record_exception(err)
                        # status API may differ by SDK version; recording exception is sufficient
                    except Exception:
                        pass
                    raise

        return tool_interceptor_tracing

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

            # Ensure OpenTelemetry trace context is propagated to downstream MCP tools
            existing_headers = mcp_tool_config.get("headers") or {}
            try:
                # inject uses the current context by default and writes W3C trace headers into the carrier
                inject(existing_headers)
                if logger.isEnabledFor(DEBUG):
                    logger.debug(
                        f"Injected OpenTelemetry context into MCP headers: {existing_headers}"
                    )
            except Exception as otel_err:
                # Do not fail tool loading if OTEL propagation fails; just log
                logger.debug(f"OTEL inject failed: {type(otel_err)} {otel_err}")

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
                logger.debug(
                    f"Loading MCP tools with Authorization header: {auth_header}"
                )

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
                tool_interceptors=[
                    self.get_tool_interceptor_truncation(),
                    self.get_tool_interceptor_tracing(),
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
