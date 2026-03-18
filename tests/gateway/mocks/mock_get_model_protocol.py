from typing import Protocol, runtime_checkable

from langchain_core.language_models import BaseChatModel

from languagemodelcommon.configs.config_schema import ChatModelConfig


@runtime_checkable
class MockGetModelProtocol(Protocol):
    def __call__(self, *, chat_model_config: ChatModelConfig) -> BaseChatModel: ...
