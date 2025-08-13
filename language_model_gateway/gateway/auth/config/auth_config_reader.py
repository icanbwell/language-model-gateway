import os

from language_model_gateway.gateway.auth.config.auth_config import AuthConfig
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)


class AuthConfigReader:
    def __init__(self, *, environment_variables: EnvironmentVariables) -> None:
        self.environment_variables = environment_variables
        assert self.environment_variables is not None, (
            "AuthConfigReader requires an EnvironmentVariables instance."
        )
        assert isinstance(self.environment_variables, EnvironmentVariables)

    def get_auth_configs_for_all_audiences(self) -> list[AuthConfig]:
        """
        Get authentication configurations for all audiences.

        Returns:
            list[AuthConfig]: A list of AuthConfig instances for each audience.
        """
        audiences: list[str] | None = self.environment_variables.auth_audiences
        assert audiences is not None, "AUTH_AUDIENCES environment variable must be set"
        auth_configs: list[AuthConfig] = []
        for audience in audiences:
            auth_config: AuthConfig | None = self.get_config_for_audience(
                audience=audience
            )
            if auth_config is not None:
                auth_configs.append(auth_config)
        return auth_configs

    # noinspection PyMethodMayBeStatic
    def get_config_for_audience(self, *, audience: str) -> AuthConfig | None:
        """
        Get the authentication configuration for a specific audience.

        Args:
            audience (str): The audience for which to retrieve the configuration.

        Returns:
            AuthConfig | None: The authentication configuration if found, otherwise None.
        """
        assert audience is not None
        # read client_id and client_secret from the environment variables
        auth_client_id: str | None = os.getenv(f"AUTH_CLIENT_ID-{audience}")
        assert auth_client_id is not None, (
            f"AUTH_CLIENT_ID-{audience} environment variable must be set"
        )
        auth_client_secret: str | None = os.getenv(f"AUTH_CLIENT_SECRET-{audience}")
        assert auth_client_secret is not None, (
            f"AUTH_CLIENT_SECRET-{audience} environment variable must be set"
        )
        auth_well_known_uri: str | None = os.getenv(f"AUTH_WELL_KNOWN_URI-{audience}")
        assert auth_well_known_uri is not None, (
            f"AUTH_WELL_KNOWN_URI-{audience} environment variable must be set"
        )
        return AuthConfig(
            audience=audience,
            client_id=auth_client_id,
            client_secret=auth_client_secret,
            well_known_uri=auth_well_known_uri,
        )
