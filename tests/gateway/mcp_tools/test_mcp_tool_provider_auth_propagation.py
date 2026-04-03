"""
Tests that AuthorizationNeededException (with login links) propagates from
MCPToolProvider.get_tools_async() instead of being silently swallowed.

When a tool config has auth_providers set (e.g., oktafhirdev) and the user
hasn't authenticated for that provider, the login link must reach the caller
so the user can be prompted to log in.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.tools import BaseTool

from languagemodelcommon.configs.schemas.config_schema import AgentConfig
from languagemodelcommon.auth.exceptions.authorization_mcp_tool_token_invalid_exception import (
    AuthorizationMcpToolTokenInvalidException,
)
from languagemodelcommon.auth.exceptions.authorization_token_cache_item_not_found_exception import (
    AuthorizationTokenCacheItemNotFoundException,
)
from languagemodelcommon.mcp.interceptors.auth import (
    AuthMcpCallInterceptor,
)
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


def _make_provider() -> MCPToolProvider:
    """Create an MCPToolProvider with mocked dependencies."""
    provider = object.__new__(MCPToolProvider)
    provider.tool_auth_manager = MagicMock()
    provider.environment_variables = MagicMock()
    provider.environment_variables.tool_call_timeout_seconds = 30
    provider.token_reducer = MagicMock()
    provider.truncation_interceptor = MagicMock()
    provider.tracing_interceptor = MagicMock()
    provider.pass_through_token_manager = MagicMock()
    return provider


@pytest.mark.parametrize(
    "exception_class,exception_kwargs,should_propagate",
    [
        pytest.param(
            AuthorizationTokenCacheItemNotFoundException,
            {
                "message": "Click here to [Login to Okta](https://okta.example.com/authorize?...)",
                "tool_auth_providers": ["oktafhirdev"],
            },
            True,
            id="token_not_found_with_login_link_propagates",
        ),
        pytest.param(
            AuthorizationMcpToolTokenInvalidException,
            {
                "message": "Authorization needed for MCP tools",
                "tool_url": "https://mcp.example.com/",
                "token": None,
            },
            False,
            id="mcp_tool_token_invalid_is_silently_skipped",
        ),
    ],
)
async def test_get_tools_async_auth_exception_propagation(
    exception_class: type,
    exception_kwargs: Dict[str, Any],
    should_propagate: bool,
) -> None:
    """Verify that AuthorizationNeededException subtypes with login links
    propagate to the caller, while AuthorizationMcpToolTokenInvalidException
    is silently skipped (existing behavior)."""
    provider = _make_provider()
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    tool_config = AgentConfig(
        name="fhir_server",
        url="https://mcpfhiragent.dev.icanbwell.com/",
        auth="jwt_token",
        auth_providers=["oktafhirdev"],
    )

    with patch.object(
        provider,
        "get_tools_by_url_async",
        new=AsyncMock(side_effect=exception_class(**exception_kwargs)),
    ):
        if should_propagate:
            with pytest.raises(ExceptionGroup) as exc_info:
                await provider.get_tools_async(
                    tools=[tool_config],
                    headers={"authorization": "Bearer some-token"},
                    auth_interceptor=auth_interceptor,
                )
            # The except* re-raise wraps the exception in an ExceptionGroup
            auth_exceptions = exc_info.value.subgroup(AuthorizationNeededException)
            assert auth_exceptions is not None
            inner = auth_exceptions.exceptions[0]
            assert "Login" in inner.message or "Authorization" in inner.message
        else:
            # Should NOT raise — tool is silently skipped
            tools = await provider.get_tools_async(
                tools=[tool_config],
                headers={"authorization": "Bearer some-token"},
                auth_interceptor=auth_interceptor,
            )
            assert tools == []


async def test_get_tools_async_loads_other_tools_before_auth_failure() -> None:
    """When multiple MCP tools are configured and one raises
    AuthorizationNeededException, tools loaded BEFORE the failing one
    should still be available (the exception terminates the loop at
    the failing tool)."""
    provider = _make_provider()
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    mock_tool = MagicMock(spec=BaseTool)
    mock_tool.name = "some_tool"

    tool_config_ok = AgentConfig(
        name="working_tool",
        url="https://working-mcp.example.com/",
    )
    tool_config_auth = AgentConfig(
        name="fhir_server",
        url="https://mcpfhiragent.dev.icanbwell.com/",
        auth="jwt_token",
        auth_providers=["oktafhirdev"],
    )

    async def mock_get_tools_by_url(
        *,
        tool_config: AgentConfig,
        headers: Dict[str, str],
        auth_interceptor: AuthMcpCallInterceptor,
    ) -> List[BaseTool]:
        if tool_config.name == "working_tool":
            return [mock_tool]
        raise AuthorizationTokenCacheItemNotFoundException(
            message="Click here to [Login](https://okta.example.com/authorize)",
            tool_auth_providers=["oktafhirdev"],
        )

    with patch.object(provider, "get_tools_by_url_async", new=mock_get_tools_by_url):
        # The auth exception should propagate even though the first tool succeeded
        with pytest.raises(ExceptionGroup) as exc_info:
            await provider.get_tools_async(
                tools=[tool_config_ok, tool_config_auth],
                headers={"authorization": "Bearer some-token"},
                auth_interceptor=auth_interceptor,
            )
        assert exc_info.value.subgroup(AuthorizationNeededException) is not None


async def test_get_tools_async_connection_error_still_skipped() -> None:
    """Non-auth exceptions (e.g., connection errors) should still be
    silently skipped — only AuthorizationNeededException propagates."""
    provider = _make_provider()
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    tool_config = AgentConfig(
        name="unreachable_tool",
        url="https://unreachable.example.com/",
    )

    with patch.object(
        provider,
        "get_tools_by_url_async",
        new=AsyncMock(side_effect=ConnectionError("Connection refused")),
    ):
        # Should NOT raise — connection errors are silently skipped
        tools = await provider.get_tools_async(
            tools=[tool_config],
            headers={},
            auth_interceptor=auth_interceptor,
        )
        assert tools == []
