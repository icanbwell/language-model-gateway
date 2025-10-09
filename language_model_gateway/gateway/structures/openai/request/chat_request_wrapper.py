import abc
from abc import abstractmethod
from typing import Literal

from openai import NotGiven
from openai.types import CompletionUsage
from openai.types.chat.completion_create_params import ResponseFormat

from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)


class ChatRequestWrapper(abc.ABC):
    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def messages(self) -> list[ChatMessageWrapper]: ...

    @messages.setter
    @abstractmethod
    def messages(self, value: list[ChatMessageWrapper]) -> None: ...

    @abstractmethod
    def append_message(self, *, message: ChatMessageWrapper) -> None: ...

    @abstractmethod
    def create_system_message(self, *, content: str) -> ChatMessageWrapper: ...

    @property
    @abstractmethod
    def stream(self) -> Literal[False, True] | None | bool: ...

    @property
    @abstractmethod
    def response_format(self) -> ResponseFormat | NotGiven: ...

    @abstractmethod
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        completion_usage_metadata: CompletionUsage,
    ) -> str: ...
