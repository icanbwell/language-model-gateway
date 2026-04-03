from unittest.mock import AsyncMock, MagicMock

import pytest

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.dcr.dcr_manager import DcrManager

from languagemodelcommon.configs.schemas.config_schema import (
    AuthenticationConfig,
    McpOAuthConfig,
)

from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


def _make_manager(
    registered_providers: dict[str, AuthConfig] | None = None,
) -> PassThroughTokenManager:
    """Build a PassThroughTokenManager with mocked dependencies."""
    registered = registered_providers or {}

    auth_config_reader = MagicMock(spec=AuthConfigReader)
    auth_config_reader.get_config_for_auth_provider.side_effect = lambda auth_provider: (
        registered.get(auth_provider)
    )
    auth_config_reader.get_auth_configs_for_all_auth_providers.return_value = list(
        registered.values()
    )

    auth_manager = MagicMock(spec=AuthManager)
    auth_manager.register_dynamic_provider = AsyncMock()

    dcr_manager = MagicMock(spec=DcrManager)
    dcr_manager.resolve_dcr_credentials = AsyncMock(return_value=None)

    tool_auth_manager = MagicMock(spec=ToolAuthManager)
    env = MagicMock(spec=LanguageModelGatewayEnvironmentVariables)

    return PassThroughTokenManager(
        auth_manager=auth_manager,
        auth_config_reader=auth_config_reader,
        tool_auth_manager=tool_auth_manager,
        environment_variables=env,
        dcr_manager=dcr_manager,
    )


def _make_oauth(
    *,
    client_id: str,
    metadata_url: str,
    display_name: str | None = None,
    audience: str | None = None,
) -> "McpOAuthConfig":
    return McpOAuthConfig.model_validate(
        {
            "clientId": client_id,
            "authServerMetadataUrl": metadata_url,
            **({"displayName": display_name} if display_name else {}),
            **({"audience": audience} if audience else {}),
        }
    )


@pytest.mark.asyncio
async def test_resolve_oauth_providers_populates_auth_providers() -> None:
    """oauth_providers on auth_config should be resolved into auth_providers."""
    manager = _make_manager()

    auth_config = AuthenticationConfig(
        name="test-model",
        auth="jwt_token",
        oauth_providers=[
            _make_oauth(
                client_id="client-a",
                metadata_url="https://idp.example.com/.well-known/openid-configuration",
                display_name="IDP A",
                audience="https://api.example.com",
            ),
            _make_oauth(
                client_id="client-b",
                metadata_url="https://cognito.example.com/.well-known/openid-configuration",
                display_name="Cognito B",
            ),
        ],
    )

    await manager._resolve_oauth_providers(auth_config)

    assert auth_config.auth_providers == ["oauth_client-a", "oauth_client-b"]
    assert manager.auth_manager.register_dynamic_provider.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_resolve_oauth_providers_uses_audience_from_config() -> None:
    """When audience is set on McpOAuthConfig, it should be used in the AuthConfig."""
    manager = _make_manager()

    auth_config = AuthenticationConfig(
        name="test-model",
        auth="jwt_token",
        oauth_providers=[
            _make_oauth(
                client_id="okta-client",
                metadata_url="https://idp.example.com/.well-known/openid-configuration",
                audience="https://idp.example.com",
                display_name="Okta",
            ),
        ],
    )

    await manager._resolve_oauth_providers(auth_config)

    call_kwargs = manager.auth_manager.register_dynamic_provider.call_args  # type: ignore[attr-defined]
    registered_config: AuthConfig = call_kwargs.kwargs["auth_config"]
    assert registered_config.audience == "https://idp.example.com"
    assert registered_config.friendly_name == "Okta"


@pytest.mark.asyncio
async def test_resolve_oauth_providers_defaults_audience_to_client_id() -> None:
    """When audience is not set, it should default to client_id."""
    manager = _make_manager()

    auth_config = AuthenticationConfig(
        name="test-model",
        auth="jwt_token",
        oauth_providers=[
            _make_oauth(
                client_id="cognito-client",
                metadata_url="https://cognito.example.com/.well-known/openid-configuration",
            ),
        ],
    )

    await manager._resolve_oauth_providers(auth_config)

    call_kwargs = manager.auth_manager.register_dynamic_provider.call_args  # type: ignore[attr-defined]
    registered_config: AuthConfig = call_kwargs.kwargs["auth_config"]
    assert registered_config.audience == "cognito-client"


@pytest.mark.asyncio
async def test_resolve_oauth_providers_skips_when_auth_providers_set() -> None:
    """If auth_providers is already set, oauth_providers should not be resolved."""
    manager = _make_manager()

    auth_config = AuthenticationConfig(
        name="test-model",
        auth="jwt_token",
        auth_providers=["existing-provider"],
        oauth_providers=[
            _make_oauth(
                client_id="should-not-register",
                metadata_url="https://idp.example.com/.well-known/openid-configuration",
            ),
        ],
    )

    await manager._resolve_oauth_providers(auth_config)

    assert auth_config.auth_providers == ["existing-provider"]
    manager.auth_manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_resolve_oauth_providers_noop_when_empty() -> None:
    """No-op when oauth_providers is not set."""
    manager = _make_manager()

    auth_config = AuthenticationConfig(
        name="test-model",
        auth="jwt_token",
    )

    await manager._resolve_oauth_providers(auth_config)

    assert auth_config.auth_providers is None
    manager.auth_manager.register_dynamic_provider.assert_not_called()  # type: ignore[attr-defined]
