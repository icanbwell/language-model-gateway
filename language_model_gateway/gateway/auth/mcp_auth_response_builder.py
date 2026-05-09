from __future__ import annotations

from httpx import Headers

from languagemodelcommon.mcp.auth.mcp_authorization_helper import (
    McpAuthorizationHelper,
)
from languagemodelcommon.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class McpAuthResponseBuilder:
    """Converts MCP auth exceptions into user-facing response content strings.

    Centralizes the exception-to-message translation that was previously
    duplicated across ChatCompletionManager and PassThroughChatCompletionsProvider.
    """

    def from_authorization_needed(
        self,
        exception: AuthorizationNeededException,
    ) -> list[str]:
        return [line.strip() for line in exception.message.splitlines() if line.strip()]

    def from_mcp_tool_unauthorized(
        self,
        exception: McpToolUnauthorizedException,
    ) -> list[str]:
        resource_metadata_url: str | None = (
            McpAuthorizationHelper.extract_resource_metadata_from_www_auth(
                headers=Headers(exception.headers)
            )
            if exception.headers
            else None
        )
        content: str = McpAuthorizationHelper.build_www_authenticate_login_message(
            resource_metadata_url=resource_metadata_url,
            tool_url=exception.url,
        )
        return [content]
