from typing import override

from tests.common import TestLanguageModelGatewayEnvironmentVariables


class MockEnvironmentVariables(TestLanguageModelGatewayEnvironmentVariables):
    @override
    @property
    def github_org(self) -> str:
        return "github_org"

    @override
    @property
    def github_token(self) -> str:
        return "github_token"

