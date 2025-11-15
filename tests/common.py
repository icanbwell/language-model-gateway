from oidcauthlib.container.container_registry import ContainerRegistry
from oidcauthlib.container.interfaces import IContainer

from language_model_gateway.container.container_factory import (
    LanguageModelGatewayContainerFactory,
)


def get_test_container() -> IContainer:
    ContainerRegistry.set_default(
        LanguageModelGatewayContainerFactory.create_container()
    )
    return ContainerRegistry.get_current()
