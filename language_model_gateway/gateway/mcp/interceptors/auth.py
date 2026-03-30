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
    at tool registration time.  This avoids blocking chat requests that never
    trigger a tool call and provides the user with actionable login URLs only
    when a tool that requires authentication is actually invoked by the LLM."""

    def __init__(
        self,
        *,
        pass_through_token_manager: PassThroughTokenManager,
    ) -> None:
        self.pass_through_token_manager = pass_through_token_manager
        if self.pass_through_token_manager is None:
            raise ValueError("pass_through_token_manager must not be None")
        if not isinstance(self.pass_through_token_manager, PassThroughTokenManager):
            raise TypeError(
                "pass_through_token_manager must be an instance of PassThroughTokenManager"
            )

        # Populated per-request by the completions provider before tools are invoked
        self._tool_configs_by_server_name: Dict[str, AgentConfig] = {}
        self._auth_information: AuthInformation | None = None
        self._headers: Dict[str, str] = {}

    def configure_for_request(
        self,
        *,
        tool_configs: list[AgentConfig],
        auth_information: AuthInformation,
        headers: Dict[str, str],
    ) -> None:
        """Set per-request context so the interceptor can resolve tokens for
        the correct tool config when a tool call arrives."""
        self._tool_configs_by_server_name = {tc.name: tc for tc in tool_configs}
        self._auth_information = auth_information
        self._headers = headers

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
            if self._auth_information is None:
                raise ValueError(
                    "AuthInformation not set on AuthMcpCallInterceptor. "
                    "Call configure_for_request before invoking tools."
                )

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

            if resolved_auth_header:
                existing_headers: Dict[str, Any] = dict(request.headers or {})
                existing_headers["Authorization"] = resolved_auth_header
                request = request.override(headers=existing_headers)

            return await handler(request)

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

        if auth_header:
            return auth_header
        return None
