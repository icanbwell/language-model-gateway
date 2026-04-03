"""Tests for McpAuthServerDiscovery — gateway wrapper around oidc-auth-lib discovery."""

from unittest.mock import AsyncMock

import pytest

from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from oidcauthlib.auth.well_known_configuration.auth_server_metadata import (
    AuthServerMetadata,
)
from languagemodelcommon.mcp.auth_server_metadata_discovery import (
    McpAuthServerDiscovery,
)


@pytest.mark.asyncio
async def test_maps_metadata_to_mcp_oauth_config() -> None:
    """Discovered metadata is correctly mapped to McpOAuthConfig."""
    mock_discovery = AsyncMock()
    mock_discovery.discover = AsyncMock(
        return_value=AuthServerMetadata(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
            registration_endpoint="https://auth.example.com/register",
            issuer="https://auth.example.com",
            scopes_supported=["openid", "profile"],
        )
    )

    discovery = McpAuthServerDiscovery(discovery=mock_discovery)
    result = await discovery.discover(mcp_server_url="https://mcp.example.com/v1/mcp")

    assert result is not None
    assert isinstance(result, McpOAuthConfig)
    assert result.authorization_url == "https://auth.example.com/authorize"
    assert result.token_url == "https://auth.example.com/token"
    assert result.registration_url == "https://auth.example.com/register"
    assert result.issuer == "https://auth.example.com"
    assert result.scopes == ["openid", "profile"]


@pytest.mark.asyncio
async def test_returns_none_when_discovery_fails() -> None:
    """Returns None when underlying discovery returns None."""
    mock_discovery = AsyncMock()
    mock_discovery.discover = AsyncMock(return_value=None)

    discovery = McpAuthServerDiscovery(discovery=mock_discovery)
    result = await discovery.discover(mcp_server_url="https://mcp.example.com/v1/mcp")

    assert result is None


@pytest.mark.asyncio
async def test_delegates_to_oidc_discovery() -> None:
    """Passes the mcp_server_url as resource_url to the oidc discovery."""
    mock_discovery = AsyncMock()
    mock_discovery.discover = AsyncMock(return_value=None)

    discovery = McpAuthServerDiscovery(discovery=mock_discovery)
    await discovery.discover(mcp_server_url="https://mcp.example.com/v1/mcp")

    mock_discovery.discover.assert_awaited_once_with(
        resource_url="https://mcp.example.com/v1/mcp"
    )


@pytest.mark.asyncio
async def test_optional_fields_none() -> None:
    """Maps correctly when optional fields are None."""
    mock_discovery = AsyncMock()
    mock_discovery.discover = AsyncMock(
        return_value=AuthServerMetadata(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
    )

    discovery = McpAuthServerDiscovery(discovery=mock_discovery)
    result = await discovery.discover(mcp_server_url="https://mcp.example.com/v1/mcp")

    assert result is not None
    assert result.registration_url is None
    assert result.issuer is None
    assert result.scopes is None
