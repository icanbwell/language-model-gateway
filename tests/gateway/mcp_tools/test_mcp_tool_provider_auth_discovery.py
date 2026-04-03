"""Tests that MCPToolProvider triggers RFC 8414 / OIDC discovery on 401
when no OAuth config is pre-configured."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from languagemodelcommon.configs.schemas.config_schema import (
    AgentConfig,
    McpOAuthConfig,
)
from languagemodelcommon.mcp.interceptors.auth import (
    AuthMcpCallInterceptor,
)
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider


def _make_oauth_config(**kwargs: Any) -> McpOAuthConfig:
    return McpOAuthConfig.model_validate(kwargs)


def _make_provider(
    *,
    discovery_result: McpOAuthConfig | None = None,
) -> MCPToolProvider:
    """Create an MCPToolProvider with mocked dependencies."""
    provider = object.__new__(MCPToolProvider)
    provider.tool_auth_manager = MagicMock()
    provider.environment_variables = MagicMock()
    provider.environment_variables.tool_call_timeout_seconds = 30
    provider.token_reducer = MagicMock()
    provider.truncation_interceptor = MagicMock()
    provider.tracing_interceptor = MagicMock()
    provider.pass_through_token_manager = MagicMock()
    provider.pass_through_token_manager._ensure_oauth_provider_registered = AsyncMock()

    mock_discovery = MagicMock()
    mock_discovery.discover = AsyncMock(return_value=discovery_result)
    provider.auth_server_metadata_discovery = mock_discovery
    return provider


def _make_401_exception_group() -> BaseExceptionGroup:
    """Create a BaseExceptionGroup containing an HTTP 401 error."""
    response = httpx.Response(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        request=httpx.Request("POST", "https://mcp.example.com/v1/mcp"),
    )
    http_error = httpx.HTTPStatusError(
        "401 Unauthorized", request=response.request, response=response
    )
    return BaseExceptionGroup("mcp errors", [http_error])


@pytest.mark.asyncio
@patch(
    "languagemodelcommon.mcp.mcp_tool_provider.MultiServerMCPClient",
)
async def test_401_no_oauth_triggers_discovery(
    mock_client_cls: MagicMock,
) -> None:
    """401 with no OAuth config triggers discovery and re-raises."""
    discovered_config = _make_oauth_config(
        authorization_url="https://auth.example.com/authorize",
        token_url="https://auth.example.com/token",
    )
    provider = _make_provider(discovery_result=discovered_config)
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    tool_config = AgentConfig(
        name="test_server",
        url="https://mcp.example.com/v1/mcp",
    )

    mock_client_cls.return_value.get_tools = AsyncMock(
        side_effect=_make_401_exception_group()
    )

    with pytest.raises(BaseException):
        await provider.get_tools_by_url_async(
            tool_config=tool_config,
            headers={},
            auth_interceptor=auth_interceptor,
        )

    # Verify discovery was called
    discover_mock: AsyncMock = provider.auth_server_metadata_discovery.discover  # type: ignore[assignment]
    discover_mock.assert_awaited_once_with(
        mcp_server_url="https://mcp.example.com/v1/mcp"
    )

    # Verify tool_config was updated
    assert tool_config.oauth is discovered_config
    assert tool_config.auth == "jwt_token"
    assert tool_config.auth_providers is not None
    assert len(tool_config.auth_providers) == 1

    # Verify provider was registered
    register_mock: AsyncMock = (
        provider.pass_through_token_manager._ensure_oauth_provider_registered  # type: ignore[assignment]
    )
    register_mock.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "languagemodelcommon.mcp.mcp_tool_provider.MultiServerMCPClient",
)
async def test_401_with_existing_oauth_skips_discovery(
    mock_client_cls: MagicMock,
) -> None:
    """401 when OAuth config is already set does not trigger discovery."""
    provider = _make_provider(
        discovery_result=_make_oauth_config(
            authorization_url="https://should-not-be-used.com/authorize",
            token_url="https://should-not-be-used.com/token",
        ),
    )
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    tool_config = AgentConfig(
        name="test_server",
        url="https://mcp.example.com/v1/mcp",
        oauth=_make_oauth_config(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
        ),
    )

    mock_client_cls.return_value.get_tools = AsyncMock(
        side_effect=_make_401_exception_group()
    )

    result = await provider.get_tools_by_url_async(
        tool_config=tool_config,
        headers={},
        auth_interceptor=auth_interceptor,
    )

    assert result == []
    discover_mock: AsyncMock = provider.auth_server_metadata_discovery.discover  # type: ignore[assignment]
    discover_mock.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "languagemodelcommon.mcp.mcp_tool_provider.MultiServerMCPClient",
)
async def test_401_discovery_returns_none_falls_through(
    mock_client_cls: MagicMock,
) -> None:
    """401 discovery returns None — falls through to return []."""
    provider = _make_provider(discovery_result=None)
    auth_interceptor = MagicMock(spec=AuthMcpCallInterceptor)

    tool_config = AgentConfig(
        name="test_server",
        url="https://mcp.example.com/v1/mcp",
    )

    mock_client_cls.return_value.get_tools = AsyncMock(
        side_effect=_make_401_exception_group()
    )

    result = await provider.get_tools_by_url_async(
        tool_config=tool_config,
        headers={},
        auth_interceptor=auth_interceptor,
    )

    assert result == []
    discover_mock: AsyncMock = provider.auth_server_metadata_discovery.discover  # type: ignore[assignment]
    discover_mock.assert_awaited_once()


class TestContainsHttp401:
    def test_direct_401(self) -> None:
        response = httpx.Response(
            401, request=httpx.Request("GET", "https://example.com")
        )
        exc = httpx.HTTPStatusError("401", request=response.request, response=response)
        eg = BaseExceptionGroup("test", [exc])
        assert MCPToolProvider._contains_http_401(eg) is True

    def test_nested_401(self) -> None:
        response = httpx.Response(
            401, request=httpx.Request("GET", "https://example.com")
        )
        exc = httpx.HTTPStatusError("401", request=response.request, response=response)
        inner = BaseExceptionGroup("inner", [exc])
        outer = BaseExceptionGroup("outer", [inner])
        assert MCPToolProvider._contains_http_401(outer) is True

    def test_non_401(self) -> None:
        response = httpx.Response(
            500, request=httpx.Request("GET", "https://example.com")
        )
        exc = httpx.HTTPStatusError("500", request=response.request, response=response)
        eg = BaseExceptionGroup("test", [exc])
        assert MCPToolProvider._contains_http_401(eg) is False

    def test_non_http_error(self) -> None:
        eg = BaseExceptionGroup("test", [ValueError("not http")])
        assert MCPToolProvider._contains_http_401(eg) is False
