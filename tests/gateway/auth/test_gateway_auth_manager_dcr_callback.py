"""Tests for GatewayTokenStorageAuthManager DCR auto-registration on callback."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)

from languagemodelcommon.auth.oauth_provider_registrar import OAuthProviderRegistrar
from languagemodelcommon.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from languagemodelcommon.configs.config_reader.mcp_json_fetcher import McpJsonFetcher
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from languagemodelcommon.configs.schemas.mcp_json_schema import (
    McpJsonConfig,
    McpServerEntry,
)
from language_model_gateway.gateway.auth.gateway_token_storage_auth_manager import (
    GatewayTokenStorageAuthManager,
)


def _build_manager(
    *,
    register_result: AuthConfig | None = None,
    register_side_effect: Exception | None = None,
    mcp_json_return: McpJsonConfig | None = None,
    plugin_names: list[str] | None = None,
) -> GatewayTokenStorageAuthManager:
    """Build a GatewayTokenStorageAuthManager with mocked dependencies."""
    env = MagicMock(spec=AbstractEnvironmentVariables)
    env.oauth_cache = "memory"
    env.auth_redirect_uri = "http://localhost/auth/callback"
    auth_config_reader = MagicMock(spec=AuthConfigReader)
    auth_config_reader.register_auth_configs = MagicMock()
    auth_config_reader.get_auth_configs_for_all_auth_providers.return_value = []
    token_reader = MagicMock(spec=TokenReader)
    token_exchange_manager = MagicMock(spec=TokenExchangeManager)
    well_known_mgr = MagicMock(spec=WellKnownConfigurationManager)

    registrar = MagicMock(spec=OAuthProviderRegistrar)
    if register_side_effect:
        registrar.register_provider = AsyncMock(side_effect=register_side_effect)
    elif register_result:
        registrar.register_provider = AsyncMock(return_value=register_result)
    else:
        registrar.register_provider = AsyncMock(
            return_value=AuthConfig(
                auth_provider="default",
                friendly_name="Default",
                audience="aud",
                client_id="default-id",
                scope="openid",
            )
        )

    fetcher = MagicMock(spec=McpJsonFetcher)
    if mcp_json_return:
        fetcher.fetch_plugins_async = AsyncMock(
            return_value={"test-plugin": mcp_json_return}
        )
    else:
        fetcher.fetch_plugins_async = AsyncMock(return_value={})

    manager = GatewayTokenStorageAuthManager(
        environment_variables=env,
        auth_config_reader=auth_config_reader,
        token_reader=token_reader,
        token_exchange_manager=token_exchange_manager,
        well_known_configuration_manager=well_known_mgr,
        oauth_provider_registrar=registrar,
        mcp_json_fetcher=fetcher,
        plugin_names=plugin_names or ["test-plugin"],
    )
    return manager


class TestTryRegisterFromMcpJsonDcr:
    """Tests for _try_register_from_mcp_json with DCR providers."""

    @pytest.mark.asyncio
    async def test_dcr_provider_delegates_to_registrar(self) -> None:
        """A DCR entry (no client_id) should delegate to OAuthProviderRegistrar."""
        result_config = AuthConfig(
            auth_provider="atlassian",
            friendly_name="Atlassian",
            audience="dcr-atlassian-id",
            client_id="dcr-atlassian-id",
            client_secret="dcr-atlassian-secret",
            scope="openid",
        )

        mcp_config = McpJsonConfig(
            mcpServers={
                "atlassian": McpServerEntry(
                    url="https://mcp.atlassian.com/v1/mcp",
                    type="http",
                    oauth=McpOAuthConfig.model_validate(
                        {
                            "clientMetadata": {
                                "clientName": "b.well Gateway",
                                "clientUri": "https://www.icanbwell.com",
                            },
                            "displayName": "Atlassian",
                        }
                    ),
                ),
            }
        )

        manager = _build_manager(
            register_result=result_config,
            mcp_json_return=mcp_config,
        )
        await manager._try_register_from_mcp_json("atlassian")

        # Should have delegated to the registrar with correct args
        registrar = manager._oauth_provider_registrar
        registrar.register_provider.assert_awaited_once()  # type: ignore[attr-defined]
        call_kwargs = registrar.register_provider.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["auth_provider"] == "atlassian"
        assert call_kwargs["server_url"] == "https://mcp.atlassian.com/v1/mcp"
        assert call_kwargs["auth_manager"] is manager

    @pytest.mark.asyncio
    async def test_pre_configured_provider_delegates_to_registrar(self) -> None:
        """Providers with a static client_id should also delegate to registrar."""
        mcp_config = McpJsonConfig(
            mcpServers={
                "github": McpServerEntry(
                    url="https://api.githubcopilot.com/mcp/",
                    type="http",
                    oauth=McpOAuthConfig.model_validate(
                        {
                            "clientId": "Iv23liP9XLkcIxslopoA",
                            "clientSecret": "ghp_secret",
                            "authorizationUrl": "https://github.com/login/oauth/authorize",
                            "tokenUrl": "https://github.com/login/oauth/access_token",
                            "displayName": "GitHub",
                        }
                    ),
                ),
            }
        )

        manager = _build_manager(mcp_json_return=mcp_config)
        await manager._try_register_from_mcp_json("mcp_oauth_Iv23liP9XLkcIxslopoA")

        registrar = manager._oauth_provider_registrar
        registrar.register_provider.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_dcr_failure_does_not_crash(self) -> None:
        """When registrar raises ValueError, the method logs and returns."""
        mcp_config = McpJsonConfig(
            mcpServers={
                "atlassian": McpServerEntry(
                    url="https://mcp.atlassian.com/v1/mcp",
                    type="http",
                    oauth=McpOAuthConfig.model_validate({"displayName": "Atlassian"}),
                ),
            }
        )

        manager = _build_manager(
            register_side_effect=ValueError("Could not resolve client_id"),
            mcp_json_return=mcp_config,
        )
        # Should not raise — just returns after logging
        await manager._try_register_from_mcp_json("atlassian")

    @pytest.mark.asyncio
    async def test_no_mcp_config_returns_without_error(self) -> None:
        """When no plugin MCP config is available, should return silently."""
        manager = _build_manager(mcp_json_return=None)
        await manager._try_register_from_mcp_json("atlassian")

        registrar = manager._oauth_provider_registrar
        registrar.register_provider.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_unmatched_provider_returns_without_error(self) -> None:
        """When auth_provider doesn't match any .mcp.json entry, should return silently."""
        mcp_config = McpJsonConfig(
            mcpServers={
                "github": McpServerEntry(
                    url="https://api.githubcopilot.com/mcp/",
                    type="http",
                    oauth=McpOAuthConfig.model_validate(
                        {"clientId": "abc123", "displayName": "GitHub"}
                    ),
                ),
            }
        )

        manager = _build_manager(mcp_json_return=mcp_config)
        await manager._try_register_from_mcp_json("nonexistent")

        registrar = manager._oauth_provider_registrar
        registrar.register_provider.assert_not_called()  # type: ignore[attr-defined]
