import logging
from typing import Callable, Awaitable, Dict, Any

from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
    ToolCallInterceptor,
)

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
        if tool_config.auth != "jwt_token" or not tool_config.auth_providers:
            return None

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
            if (
                tool_config is None
                or tool_config.auth != "jwt_token"
                or not tool_config.auth_providers
            ):
                return await handler(request)

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
                existing_headers: Dict[str, Any] = dict(request.headers or {})
                existing_headers["Authorization"] = resolved_auth_header
                modified_request = request.override(headers=existing_headers)

            return await handler(modified_request)

        return tool_interceptor_auth

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
