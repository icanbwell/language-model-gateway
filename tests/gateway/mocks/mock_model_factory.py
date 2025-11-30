from typing import override

from langchain_core.language_models import BaseChatModel

from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.models.model_factory import ModelFactory
from tests.gateway.mocks.mock_get_model_protocol import MockGetModelProtocol


class MockModelFactory(ModelFactory):
    def __init__(self, *, fn_get_model: MockGetModelProtocol) -> None:
        super().__init__()
        self.fn_get_model: MockGetModelProtocol = fn_get_model
        assert self.fn_get_model is not None
        assert isinstance(self.fn_get_model, MockGetModelProtocol)

    @override
    def get_model(self, chat_model_config: ChatModelConfig) -> BaseChatModel:
        return self.fn_get_model(chat_model_config=chat_model_config)
