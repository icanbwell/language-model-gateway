import logging
from typing import Callable, Awaitable, Dict, Any

from httpx import HTTPStatusError
from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
    ToolCallInterceptor,
)
from mcp.types import CallToolResult, TextContent

from languagemodelcommon.configs.schemas.config_schema import AgentConfig
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.models.token import Token
from oidcauthlib.auth.token_reader import TokenReader

from language_model_gateway.gateway.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class AuthMcpCallInterceptor:
    """Resolves authentication tokens at MCP tool invocation time rather than
    at tool registration time.  Created per-request with the request's auth
    context so there is no shared mutable state between concurrent requests."""

    def __init__(
        self,
        *,
        pass_through_token_manager: PassThroughTokenManager,
        tool_configs: list[AgentConfig],
        auth_information: AuthInformation,
        headers: Dict[str, str],
    ) -> None:
        self.pass_through_token_manager = pass_through_token_manager
        if self.pass_through_token_manager is None:
            raise ValueError("pass_through_token_manager must not be None")
        if not isinstance(self.pass_through_token_manager, PassThroughTokenManager):
            raise TypeError(
                "pass_through_token_manager must be an instance of PassThroughTokenManager"
            )
        self._tool_configs_by_server_name: Dict[str, AgentConfig] = {
            tc.name: tc for tc in tool_configs
        }
        self._auth_information = auth_information
        self._headers = headers

    async def resolve_auth_header_for_discovery(
        self, tool_config: AgentConfig
    ) -> str | None:
        """Resolve the Authorization header for tool discovery (listing tools).

        Uses the same token resolution logic as the invocation-time
        interceptor so that MCP servers requiring auth for ``tools/list``
        receive a valid token during discovery.  Returns ``None`` when
        auth context is incomplete (e.g. no subject) so that discovery
        can proceed unauthenticated and the MCP server's rejection is
        handled by the caller's error-handling path."""
        if tool_config.auth != "jwt_token":
            return None

        if not tool_config.auth_providers:
            return self._extract_auth_header(self._headers)

        auth_header = self._extract_auth_header(self._headers)

        try:
            token_cache_item: (
                TokenCacheItem | None
            ) = await self.pass_through_token_manager.check_tokens_are_valid_for_tool(
                auth_header=auth_header,
                auth_information=self._auth_information,
                authentication_config=tool_config,
            )
        except (ValueError, AuthorizationMcpToolTokenInvalidException) as e:
            logger.info(
                f"Could not resolve auth for discovery of {tool_config.name}: {e}"
            )
            return None

        return self._resolve_auth_header(
            token_cache_item=token_cache_item,
            auth_header=auth_header,
            tool_config=tool_config,
        )

    def get_tool_interceptor_auth(self) -> ToolCallInterceptor:
        async def tool_interceptor_auth(
            request: MCPToolCallRequest,
            handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
        ) -> MCPToolCallResult:
            tool_config = self._tool_configs_by_server_name.get(request.server_name)
            if tool_config is None or tool_config.auth != "jwt_token":
                return await self._call_handler_with_auth_error_handling(
                    handler=handler, request=request
                )

            if not tool_config.auth_providers:
                auth_header = self._extract_auth_header(self._headers)
                if auth_header:
                    existing_headers: Dict[str, Any] = dict(request.headers or {})
                    existing_headers["Authorization"] = auth_header
                    request = request.override(headers=existing_headers)
                return await self._call_handler_with_auth_error_handling(
                    handler=handler, request=request
                )

            auth_header = self._extract_auth_header(self._headers)

            token_cache_item: (
                TokenCacheItem | None
            ) = await self.pass_through_token_manager.check_tokens_are_valid_for_tool(
                auth_header=auth_header,
                auth_information=self._auth_information,
                authentication_config=tool_config,
            )

            resolved_auth_header = self._resolve_auth_header(
                token_cache_item=token_cache_item,
                auth_header=auth_header,
                tool_config=tool_config,
            )

            modified_request = request
            if resolved_auth_header:
                existing_headers = dict(request.headers or {})
                existing_headers["Authorization"] = resolved_auth_header
                modified_request = request.override(headers=existing_headers)

            return await self._call_handler_with_auth_error_handling(
                handler=handler, request=modified_request
            )

        return tool_interceptor_auth

    @staticmethod
    async def _call_handler_with_auth_error_handling(
        *,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
        request: MCPToolCallRequest,
    ) -> MCPToolCallResult:
        try:
            return await handler(request)
        except BaseExceptionGroup as eg:
            http_auth_error = AuthMcpCallInterceptor._extract_http_auth_error(eg)
            if http_auth_error is not None:
                url = str(http_auth_error.request.url)
                status = http_auth_error.response.status_code
                www_authenticate = http_auth_error.response.headers.get(
                    "WWW-Authenticate"
                )
                logger.warning(
                    "MCP tool call to %s returned HTTP %s (WWW-Authenticate: %s): %s",
                    url,
                    status,
                    www_authenticate,
                    http_auth_error,
                )
                auth_detail = ""
                if www_authenticate:
                    auth_detail = f" WWW-Authenticate: {www_authenticate}"
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Authorization failed (HTTP {status}) for MCP tool at {url}."
                            f" The user's credentials were rejected by the server."
                            f"{auth_detail}"
                            f" Please ask the user to check their authentication or log in again.",
                        )
                    ],
                    isError=True,
                )
            raise

    @staticmethod
    def _extract_http_auth_error(
        eg: BaseExceptionGroup,
    ) -> HTTPStatusError | None:
        for exc in eg.exceptions:
            if isinstance(exc, BaseExceptionGroup):
                result = AuthMcpCallInterceptor._extract_http_auth_error(exc)
                if result is not None:
                    return result
            elif isinstance(exc, HTTPStatusError) and exc.response.status_code in (
                401,
                403,
            ):
                return exc
        return None

    @staticmethod
    def _extract_auth_header(headers: Dict[str, str]) -> str | None:
        auth_headers = [
            headers.get(key) for key in headers if key.lower() == "authorization"
        ]
        return auth_headers[0] if auth_headers else None

    @staticmethod
    def _resolve_auth_header(
        *,
        token_cache_item: TokenCacheItem | None,
        auth_header: str | None,
        tool_config: AgentConfig,
    ) -> str | None:
        if token_cache_item is not None:
            token: Token | None = token_cache_item.get_access_token()
            if token:
                return f"Bearer {token.token}"

        auth_bearer_token: str | None = TokenReader.extract_token(
            authorization_header=auth_header
        )
        auth_token: Token | None = (
            Token.create_from_token(token=auth_bearer_token)
            if auth_bearer_token and auth_bearer_token != "fake-api-key"
            else None
        )

        if not auth_token and not tool_config.auth_optional:
            url = tool_config.url or "unknown"
            raise AuthorizationMcpToolTokenInvalidException(
                message=f"No token found. Authorization needed for MCP tools at {url}"
                f" for auth providers {tool_config.auth_providers}",
                tool_url=url,
                token=None,
            )

        if auth_token and auth_header:
            return auth_header
        return None
