import uuid
from typing import List, override

from simple_container.container.simple_container import SimpleContainer
from simple_container.container.interfaces import IContainer
from oidcauthlib.utilities.environment.oidc_environment_variables import (
    OidcEnvironmentVariables,
)
from languagemodelcommon.configs.config_reader.config_reader import ConfigReader
from languagemodelcommon.configs.schemas.config_schema import ChatModelConfig
from languagemodelcommon.utilities.environment.language_model_common_environment_variables import (
    LanguageModelCommonEnvironmentVariables,
)

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

    @override
    @property
    def snapshot_cache_type(self) -> str:
        return "memory"


def create_test_container() -> SimpleContainer:
    container: SimpleContainer = LanguageModelGatewayContainerFactory.create_container(
        source=f"{__name__}[{uuid.uuid4().hex}]"
    )
    test_language_model_gateway_environment_variables = (
        TestLanguageModelGatewayEnvironmentVariables()
    )
    container.singleton(
        OidcEnvironmentVariables,
        lambda c: test_language_model_gateway_environment_variables,
    )
    container.singleton(
        LanguageModelGatewayEnvironmentVariables,
        lambda c: test_language_model_gateway_environment_variables,
    )
    container.singleton(
        LanguageModelCommonEnvironmentVariables,
        lambda c: test_language_model_gateway_environment_variables,
    )
    return container


async def set_model_configs(
    container: IContainer, configs: List[ChatModelConfig]
) -> None:
    """Write model configs to the ConfigReader's snapshot cache.

    Replaces the old pattern of writing to ConfigExpiringCache which is
    no longer read by ConfigReader.
    """
    config_reader: ConfigReader = container.resolve(ConfigReader)
    await config_reader.clear_cache()
    await config_reader._write_to_snapshot_cache(configs)
