import logging
from logging import DEBUG
from typing import List, Callable, Awaitable, Any

from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
    ToolCallInterceptor,
)
from mcp.types import (
    ContentBlock,
    TextContent,
    EmbeddedResource,
    TextResourceContents,
    CallToolResult,
)

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class TruncationMcpCallInterceptor:
    def __init__(
        self,
        *,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        token_reducer: TokenReducer,
    ) -> None:
        self.environment_variables = environment_variables
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                f"environment_variables must be LanguageModelGatewayEnvironmentVariables, got {type(self.environment_variables)}"
            )
        self.token_reducer = token_reducer
        if self.token_reducer is None:
            raise ValueError("token_reducer must not be None")
        if not isinstance(self.token_reducer, TokenReducer):
            raise TypeError(
                f"token_reducer must be TokenReducer, got {type(self.token_reducer)}"
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
                    if max_token_limit > 0 >= tokens_limit_left:
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
