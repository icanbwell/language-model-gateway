"""Tests for OAuth 2.1 dynamic provider registration in PassThroughTokenManager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.dcr.dcr_manager import DcrManager
from oidcauthlib.auth.dcr.dcr_registration import DcrRegistration

from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)


def _build_manager(
    *,
    existing_config: AuthConfig | None = None,
    dcr_result: DcrRegistration | None = None,
) -> PassThroughTokenManager:
    """Create a PassThroughTokenManager with mocked dependencies."""
    auth_manager = MagicMock()
    auth_manager.register_dynamic_provider = AsyncMock()

    auth_config_reader = MagicMock()
    configs: list[AuthConfig] = []
    if existing_config:
        configs.append(existing_config)
    auth_config_reader.get_config_for_auth_provider.return_value = existing_config
    auth_config_reader.get_auth_configs_for_all_auth_providers.return_value = configs

    tool_auth_manager = MagicMock()
    environment_variables = MagicMock()
    environment_variables.app_login_uri = None
    environment_variables.app_token_save_uri = None

    dcr_manager = MagicMock(spec=DcrManager)
    dcr_manager.resolve_dcr_credentials = AsyncMock(return_value=dcr_result)

    manager = object.__new__(PassThroughTokenManager)
    manager.auth_manager = auth_manager
    manager.auth_config_reader = auth_config_reader
    manager.tool_auth_manager = tool_auth_manager
    manager.environment_variables = environment_variables
    manager.dcr_manager = dcr_manager

    return manager


class TestEnsureOAuthProviderRegistered:
    """Tests for _ensure_oauth_provider_registered method."""

    @pytest.mark.asyncio
    async def test_returns_existing_config(self) -> None:
        existing = AuthConfig(
            auth_provider="existing",
            friendly_name="Existing",
            audience="aud",
            client_id="cid",
            well_known_uri="https://idp.example.com/.well-known/openid-configuration",
        )
        manager = _build_manager(existing_config=existing)
        oauth = McpOAuthConfig(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="existing", oauth=oauth
        )

        assert result is existing
        manager.dcr_manager.resolve_dcr_credentials.assert_not_called()
        manager.auth_manager.register_dynamic_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_registered_client_uses_config_client_id(self) -> None:
        manager = _build_manager()
        oauth = McpOAuthConfig.model_validate(
            {
                "clientId": "pre-registered-id",
                "clientSecret": "secret",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
                "scopes": ["read", "write"],
            }
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="mcp_oauth_pre-registered-id", oauth=oauth
        )

        assert result.client_id == "pre-registered-id"
        assert result.client_secret == "secret"
        assert result.authorization_endpoint == "https://auth.example.com/authorize"
        assert result.token_endpoint == "https://auth.example.com/token"
        assert result.scope == "read write"
        manager.auth_manager.register_dynamic_provider.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dcr_uses_resolved_credentials(self) -> None:
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-client-id"
        dcr_reg.client_secret = "dcr-secret"

        manager = _build_manager(dcr_result=dcr_reg)
        oauth = McpOAuthConfig.model_validate(
            {
                "registrationUrl": "https://auth.example.com/register",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
                "scopes": ["mcp:read"],
                "usePKCE": True,
                "pkceMethod": "S256",
            }
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="dcr-server", oauth=oauth
        )

        assert result.client_id == "dcr-client-id"
        assert result.client_secret == "dcr-secret"
        assert result.use_pkce is True
        assert result.pkce_method == "S256"
        assert result.registration_url == "https://auth.example.com/register"
        manager.dcr_manager.resolve_dcr_credentials.assert_awaited_once()
        manager.auth_manager.register_dynamic_provider.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_no_client_id_resolved(self) -> None:
        manager = _build_manager(dcr_result=None)
        oauth = McpOAuthConfig(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
        )

        with pytest.raises(ValueError, match="Could not resolve client_id"):
            await manager._ensure_oauth_provider_registered(
                auth_provider="no-creds", oauth=oauth
            )

    @pytest.mark.asyncio
    async def test_dedup_prevents_duplicate_config_append(self) -> None:
        manager = _build_manager()
        oauth = McpOAuthConfig.model_validate(
            {
                "clientId": "cid",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
        )

        # Register twice
        await manager._ensure_oauth_provider_registered(
            auth_provider="prov", oauth=oauth
        )
        # Second call: existing_config lookup still returns None (mock),
        # but the config list now has the entry from first call
        await manager._ensure_oauth_provider_registered(
            auth_provider="prov", oauth=oauth
        )

        configs = manager.auth_config_reader.get_auth_configs_for_all_auth_providers()
        prov_configs = [c for c in configs if c.auth_provider == "prov"]
        assert len(prov_configs) == 1
