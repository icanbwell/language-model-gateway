import uuid
from typing import override

from oidcauthlib.container.simple_container import SimpleContainer
from oidcauthlib.utilities.environment.environment_variables import EnvironmentVariables

from language_model_gateway.container.container_factory import (
    LanguageModelGatewayContainerFactory,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


class TestLanguageModelGatewayEnvironmentVariables(
    LanguageModelGatewayEnvironmentVariables
):
    """Test Language Model Gateway Environment Variables"""

    @override
    @property
    def llm_storage_type(self) -> str:
        return "memory"


def create_test_container() -> SimpleContainer:
    container: SimpleContainer = LanguageModelGatewayContainerFactory.create_container(
        source=f"{__name__}[{uuid.uuid4().hex}]"
    )
    test_language_model_gateway_environment_variables = (
        TestLanguageModelGatewayEnvironmentVariables()
    )
    container.singleton(
        EnvironmentVariables,
        lambda c: test_language_model_gateway_environment_variables,
    )
    container.singleton(
        LanguageModelGatewayEnvironmentVariables,
        lambda c: test_language_model_gateway_environment_variables,
    )
    return container
