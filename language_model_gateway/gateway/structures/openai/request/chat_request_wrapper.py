import abc
from abc import abstractmethod
from typing import Literal, Any, List, Optional

from langchain_core.messages import AnyMessage
from langchain_core.messages.ai import UsageMetadata

from language_model_gateway.configs.config_schema import AgentConfig
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
    def response_format(
        self,
    ) -> Literal["text", "json_object", "json_schema"] | None: ...

    @property
    @abstractmethod
    def response_json_schema(self) -> str | None: ...

    @abstractmethod
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
    ) -> str: ...

    @abstractmethod
    def create_final_sse_message(
        self,
        *,
        request_id: str,
        usage_metadata: UsageMetadata | None,
    ) -> str: ...

    @abstractmethod
    def create_non_streaming_response(
        self,
        *,
        request_id: str,
        json_output_requested: Optional[bool],
        responses: List[AnyMessage],
    ) -> dict[str, Any]: ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_tools(self) -> list[AgentConfig]: ...
