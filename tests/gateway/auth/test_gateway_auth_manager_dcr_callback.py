"""Tests for GatewayTokenStorageAuthManager DCR auto-registration on callback."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.dcr.dcr_manager import DcrManager
from oidcauthlib.auth.dcr.dcr_registration import DcrRegistration
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)

from languagemodelcommon.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
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
    dcr_result: DcrRegistration | None = None,
    discovery_result: McpOAuthConfig | None = None,
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

    dcr_manager = MagicMock(spec=DcrManager)
    dcr_manager.resolve_dcr_credentials = AsyncMock(return_value=dcr_result)

    auth_server_discovery = MagicMock()
    auth_server_discovery.discover = AsyncMock(return_value=discovery_result)

    manager = GatewayTokenStorageAuthManager(
        environment_variables=env,
        auth_config_reader=auth_config_reader,
        token_reader=token_reader,
        token_exchange_manager=token_exchange_manager,
        well_known_configuration_manager=well_known_mgr,
        dcr_manager=dcr_manager,
        auth_server_metadata_discovery=auth_server_discovery,
    )
    manager.register_dynamic_provider = AsyncMock()  # type: ignore[method-assign]
    return manager


class TestTryRegisterFromMcpJsonDcr:
    """Tests for _try_register_from_mcp_json with DCR providers."""

    @pytest.mark.asyncio
    async def test_dcr_provider_registers_via_discovery_and_dcr(self) -> None:
        """A DCR entry (no client_id) should discover endpoints and perform DCR."""
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-atlassian-id"
        dcr_reg.client_secret = "dcr-atlassian-secret"

        discovered = McpOAuthConfig.model_validate(
            {
                "registrationUrl": "https://mcp.atlassian.com/register",
                "authorizationUrl": "https://auth.atlassian.com/authorize",
                "tokenUrl": "https://auth.atlassian.com/token",
                "issuer": "https://auth.atlassian.com",
            }
        )

        manager = _build_manager(dcr_result=dcr_reg, discovery_result=discovered)

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

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=mcp_config,
        ):
            await manager._try_register_from_mcp_json("atlassian")

        # Discovery should have been called with the MCP server URL
        manager._auth_server_metadata_discovery.discover.assert_awaited_once_with(  # type: ignore[union-attr]
            mcp_server_url="https://mcp.atlassian.com/v1/mcp",
        )

        # DCR should have been called with client metadata
        dcr_kwargs = manager._dcr_manager.resolve_dcr_credentials.call_args.kwargs  # type: ignore[union-attr]
        assert dcr_kwargs["auth_provider"] == "atlassian"
        assert dcr_kwargs["registration_url"] == "https://mcp.atlassian.com/register"
        assert dcr_kwargs["client_name"] == "b.well Gateway"
        assert dcr_kwargs["client_uri"] == "https://www.icanbwell.com"

        # Should have registered the provider
        manager.register_dynamic_provider.assert_awaited_once()  # type: ignore[attr-defined]
        call_kwargs = manager.register_dynamic_provider.call_args.kwargs  # type: ignore[attr-defined]
        auth_config: AuthConfig = call_kwargs["auth_config"]
        assert auth_config.auth_provider == "atlassian"
        assert auth_config.client_id == "dcr-atlassian-id"
        assert auth_config.client_secret == "dcr-atlassian-secret"

    @pytest.mark.asyncio
    async def test_pre_configured_provider_still_works(self) -> None:
        """Providers with a static client_id should still register without DCR."""
        manager = _build_manager()

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

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=mcp_config,
        ):
            await manager._try_register_from_mcp_json("mcp_oauth_Iv23liP9XLkcIxslopoA")

        # DCR should NOT have been called
        manager._dcr_manager.resolve_dcr_credentials.assert_not_called()  # type: ignore[union-attr]

        # Should have registered the provider
        manager.register_dynamic_provider.assert_awaited_once()  # type: ignore[attr-defined]
        call_kwargs = manager.register_dynamic_provider.call_args.kwargs  # type: ignore[attr-defined]
        auth_config: AuthConfig = call_kwargs["auth_config"]
        assert auth_config.client_id == "Iv23liP9XLkcIxslopoA"

    @pytest.mark.asyncio
    async def test_dcr_without_managers_logs_warning(self) -> None:
        """DCR entry without dcr_manager/discovery should log warning and not crash."""
        env = MagicMock(spec=AbstractEnvironmentVariables)
        env.oauth_cache = "memory"
        env.auth_redirect_uri = "http://localhost/auth/callback"
        auth_config_reader = MagicMock(spec=AuthConfigReader)
        auth_config_reader.get_auth_configs_for_all_auth_providers.return_value = []
        token_reader = MagicMock(spec=TokenReader)
        token_exchange_manager = MagicMock(spec=TokenExchangeManager)
        well_known_mgr = MagicMock(spec=WellKnownConfigurationManager)

        # No DCR manager or discovery injected
        manager = GatewayTokenStorageAuthManager(
            environment_variables=env,
            auth_config_reader=auth_config_reader,
            token_reader=token_reader,
            token_exchange_manager=token_exchange_manager,
            well_known_configuration_manager=well_known_mgr,
        )
        manager.register_dynamic_provider = AsyncMock()  # type: ignore[method-assign]

        mcp_config = McpJsonConfig(
            mcpServers={
                "atlassian": McpServerEntry(
                    url="https://mcp.atlassian.com/v1/mcp",
                    type="http",
                    oauth=McpOAuthConfig.model_validate({"displayName": "Atlassian"}),
                ),
            }
        )

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=mcp_config,
        ):
            # Should not raise — just returns without registering
            await manager._try_register_from_mcp_json("atlassian")

        manager.register_dynamic_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_dcr_failure_does_not_register(self) -> None:
        """When DCR fails to resolve a client_id, no registration should happen."""
        manager = _build_manager(dcr_result=None, discovery_result=None)

        mcp_config = McpJsonConfig(
            mcpServers={
                "atlassian": McpServerEntry(
                    url="https://mcp.atlassian.com/v1/mcp",
                    type="http",
                    oauth=McpOAuthConfig.model_validate({"displayName": "Atlassian"}),
                ),
            }
        )

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=mcp_config,
        ):
            await manager._try_register_from_mcp_json("atlassian")

        manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_no_mcp_json_returns_without_error(self) -> None:
        """When .mcp.json is not found, should return silently."""
        manager = _build_manager()

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=None,
        ):
            await manager._try_register_from_mcp_json("atlassian")

        manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_unmatched_provider_returns_without_error(self) -> None:
        """When auth_provider doesn't match any .mcp.json entry, should return silently."""
        manager = _build_manager()

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

        with patch(
            "language_model_gateway.gateway.auth.gateway_token_storage_auth_manager.read_mcp_json",
            return_value=mcp_config,
        ):
            await manager._try_register_from_mcp_json("nonexistent")

        manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]
