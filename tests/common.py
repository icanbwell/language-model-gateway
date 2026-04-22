import uuid
from typing import override

from langchain_ai_skills_framework.loaders.null_plugin_skill_store import (
    NullPluginSkillStore,
)
from langchain_ai_skills_framework.loaders.plugin_skill_store import PluginSkillStore
from simple_container.container.simple_container import SimpleContainer
from oidcauthlib.utilities.environment.oidc_environment_variables import (
    OidcEnvironmentVariables,
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
    # Use NullPluginSkillStore to avoid requiring MongoDB during tests
    container.singleton(
        PluginSkillStore,
        lambda c: NullPluginSkillStore(),
    )
    return container
