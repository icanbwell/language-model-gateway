from typing import override

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


class MockEnvironmentVariables(LanguageModelGatewayEnvironmentVariables):
    @override
    @property
    def github_org(self) -> str:
        return "github_org"

    @override
    @property
    def github_token(self) -> str:
        return "github_token"
