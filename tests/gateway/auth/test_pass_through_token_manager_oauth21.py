"""Tests for OAuth 2.1 dynamic provider registration in PassThroughTokenManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.dcr.dcr_manager import DcrManager
from oidcauthlib.auth.dcr.dcr_registration import DcrRegistration

from languagemodelcommon.auth.tools.tool_auth_manager import ToolAuthManager
from languagemodelcommon.auth.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


def _build_manager(
    *,
    existing_config: AuthConfig | None = None,
    dcr_result: DcrRegistration | None = None,
) -> PassThroughTokenManager:
    """Create a PassThroughTokenManager with spec-based mocks that pass isinstance checks."""
    auth_manager = MagicMock(spec=AuthManager)
    auth_manager.register_dynamic_provider = AsyncMock()

    auth_config_reader = MagicMock(spec=AuthConfigReader)
    configs: list[AuthConfig] = []
    if existing_config:
        configs.append(existing_config)
    auth_config_reader.get_config_for_auth_provider.return_value = existing_config
    auth_config_reader.get_auth_configs_for_all_auth_providers.return_value = configs

    tool_auth_manager = MagicMock(spec=ToolAuthManager)

    environment_variables = MagicMock(spec=LanguageModelGatewayEnvironmentVariables)
    environment_variables.app_login_uri = None
    environment_variables.app_token_save_uri = None

    dcr_manager = MagicMock(spec=DcrManager)
    dcr_manager.resolve_dcr_credentials = AsyncMock(return_value=dcr_result)

    return PassThroughTokenManager(
        auth_manager=auth_manager,
        auth_config_reader=auth_config_reader,
        tool_auth_manager=tool_auth_manager,
        environment_variables=environment_variables,
        dcr_manager=dcr_manager,
    )


class TestEnsureOAuthProviderRegistered:
    """Tests for _ensure_oauth_provider_registered method."""

    @pytest.mark.asyncio
    async def test_returns_existing_config(self) -> None:
        existing = AuthConfig(
            auth_provider="existing",
            friendly_name="Existing",
            audience="aud",
            client_id="cid",
            scope="openid",
            well_known_uri="https://idp.example.com/.well-known/openid-configuration",
        )
        manager = _build_manager(existing_config=existing)
        oauth = McpOAuthConfig.model_validate(
            {
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="existing", oauth=oauth
        )

        assert result is existing
        manager.dcr_manager.resolve_dcr_credentials.assert_not_called()  # type: ignore[attr-defined]
        manager.auth_manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]

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
        manager.auth_manager.register_dynamic_provider.assert_awaited_once()  # type: ignore[attr-defined]

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
        manager.dcr_manager.resolve_dcr_credentials.assert_awaited_once()  # type: ignore[attr-defined]
        # When no clientMetadata is provided, client_name should default
        # to the auth_provider key so the auth server shows a meaningful name.
        call_kwargs = manager.dcr_manager.resolve_dcr_credentials.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["client_name"] == "dcr-server"
        manager.auth_manager.register_dynamic_provider.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_dcr_sends_explicit_client_metadata(self) -> None:
        """When clientMetadata.client_name is set it takes precedence over defaults."""
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-meta-id"
        dcr_reg.client_secret = "dcr-meta-secret"

        manager = _build_manager(dcr_result=dcr_reg)
        oauth = McpOAuthConfig.model_validate(
            {
                "registrationUrl": "https://auth.example.com/register",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
                "clientMetadata": {
                    "clientName": "b.well Health Gateway",
                    "clientUri": "https://www.icanbwell.com",
                },
            }
        )

        await manager._ensure_oauth_provider_registered(
            auth_provider="meta-test", oauth=oauth
        )

        call_kwargs = manager.dcr_manager.resolve_dcr_credentials.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["client_name"] == "b.well Health Gateway"
        assert call_kwargs["client_uri"] == "https://www.icanbwell.com"

    @pytest.mark.asyncio
    async def test_dcr_client_name_falls_back_to_display_name(self) -> None:
        """When no clientMetadata but displayName is set, client_name uses displayName."""
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-display-id"
        dcr_reg.client_secret = "dcr-display-secret"

        manager = _build_manager(dcr_result=dcr_reg)
        oauth = McpOAuthConfig.model_validate(
            {
                "registrationUrl": "https://auth.example.com/register",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
                "displayName": "My FHIR Server",
            }
        )

        await manager._ensure_oauth_provider_registered(
            auth_provider="display-test", oauth=oauth
        )

        call_kwargs = manager.dcr_manager.resolve_dcr_credentials.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["client_name"] == "My FHIR Server"

    @pytest.mark.asyncio
    async def test_raises_when_no_client_id_resolved(self) -> None:
        manager = _build_manager(dcr_result=None)
        oauth = McpOAuthConfig.model_validate(
            {
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
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

    @pytest.mark.asyncio
    async def test_dcr_overrides_config_client_id(self) -> None:
        """When both config client_id and DCR result are present, DCR takes precedence."""
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-overridden-id"
        dcr_reg.client_secret = "dcr-secret"

        manager = _build_manager(dcr_result=dcr_reg)
        oauth = McpOAuthConfig.model_validate(
            {
                "clientId": "config-client-id",
                "registrationUrl": "https://auth.example.com/register",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="override-test", oauth=oauth
        )

        assert result.client_id == "dcr-overridden-id"
        assert result.client_secret == "dcr-secret"

    @pytest.mark.asyncio
    async def test_pkce_defaults(self) -> None:
        """PKCE defaults to enabled with S256 when not explicitly set."""
        manager = _build_manager()
        oauth = McpOAuthConfig.model_validate(
            {
                "clientId": "pkce-test",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
        )

        result = await manager._ensure_oauth_provider_registered(
            auth_provider="pkce-default", oauth=oauth
        )

        assert result.use_pkce is True
        assert result.pkce_method == "S256"

    @pytest.mark.asyncio
    async def test_concurrent_dcr_only_registers_once(self) -> None:
        """Concurrent requests for the same provider only trigger DCR once.

        Simulates multiple users hitting the same MCP server at once.
        The per-provider lock should serialize the calls so only the
        first actually performs DCR; subsequent waiters find the
        already-registered config.
        """
        dcr_reg = MagicMock(spec=DcrRegistration)
        dcr_reg.client_id = "dcr-single-id"
        dcr_reg.client_secret = "dcr-secret"

        manager = _build_manager(dcr_result=dcr_reg)

        # Track how many times DCR is actually called
        call_count = 0
        original_resolve = manager.dcr_manager.resolve_dcr_credentials

        async def counting_resolve(**kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            result = await original_resolve(**kwargs)
            # After the first call completes, simulate the config being
            # registered in-memory so subsequent lock waiters find it.
            registered = AuthConfig(
                auth_provider=kwargs["auth_provider"],
                friendly_name=kwargs["auth_provider"],
                audience="dcr-single-id",
                client_id="dcr-single-id",
                client_secret="dcr-secret",
                scope="openid",
                authorization_endpoint="https://auth.example.com/authorize",
                token_endpoint="https://auth.example.com/token",
            )
            manager.auth_config_reader.get_config_for_auth_provider.return_value = (  # type: ignore[attr-defined]
                registered
            )
            return result

        manager.dcr_manager.resolve_dcr_credentials = AsyncMock(  # type: ignore[method-assign]
            side_effect=counting_resolve,
        )

        oauth = McpOAuthConfig.model_validate(
            {
                "registrationUrl": "https://auth.example.com/register",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
            }
        )

        # Fire 5 concurrent registrations for the same provider
        tasks = [
            manager._ensure_oauth_provider_registered(
                auth_provider="concurrent-test", oauth=oauth
            )
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should resolve to a valid config
        assert all(r.client_id == "dcr-single-id" for r in results)
        # DCR should have been called exactly once
        assert call_count == 1
