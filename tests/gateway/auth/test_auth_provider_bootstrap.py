from unittest.mock import MagicMock

from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)

from languagemodelcommon.configs.config_reader.mcp_json_reader import (  # type: ignore[attr-defined]
    McpJsonConfig,
    build_auth_configs_from_mcp_json,
)


def test_mcp_json_auth_configs_registered_into_reader() -> None:
    """Auth providers from .mcp.json are registered into AuthConfigReader."""
    mcp_config = McpJsonConfig.model_validate(
        {
            "mcpServers": {},
            "authProviders": {
                "oktafhirdev": {
                    "issuer": "https://icanbwell.okta.com",
                    "audience": "https://icanbwell.okta.com",
                    "clientId": "0oarf29h6x2DaWCkT697",
                    "wellKnownUri": "https://icanbwell.okta.com/.well-known/openid-configuration",
                    "scope": "openid email profile groups",
                    "friendlyName": "Okta FHIR Dev",
                },
                "client1": {
                    "issuer": "http://keycloak:8080/realms/bwell-realm",
                    "audience": "client1",
                    "clientId": "bwell-client-id",
                    "clientSecret": "bwell-secret",
                    "wellKnownUri": "http://keycloak:8080/realms/bwell-realm/.well-known/openid-configuration",
                    "scope": "openid email profile",
                },
            },
        }
    )

    # Build configs from .mcp.json
    auth_configs = build_auth_configs_from_mcp_json(mcp_config)
    assert len(auth_configs) == 2

    # Create a reader with a mock that passes isinstance checks
    env = MagicMock(spec=AbstractEnvironmentVariables)
    env.auth_providers = None
    reader = AuthConfigReader(environment_variables=env)

    # Register the configs
    reader.register_auth_configs(  # type: ignore[attr-defined]
        configs=auth_configs
    )

    # Verify they are accessible
    all_configs = reader.get_auth_configs_for_all_auth_providers()
    assert len(all_configs) == 2

    okta = reader.get_config_for_auth_provider(auth_provider="oktafhirdev")
    assert okta is not None
    assert okta.client_id == "0oarf29h6x2DaWCkT697"
    assert okta.issuer == "https://icanbwell.okta.com"

    kc = reader.get_config_for_auth_provider(auth_provider="client1")
    assert kc is not None
    assert kc.client_secret == "bwell-secret"
