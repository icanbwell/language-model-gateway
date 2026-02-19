import abc
from abc import abstractmethod
from typing import AsyncIterable, Literal, Any, List, Optional

from langchain_core.messages import AnyMessage
from langchain_core.messages.ai import UsageMetadata
from starlette.responses import StreamingResponse, JSONResponse

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

    @abstractmethod
    def stream_response(
        self,
        *,
        response_messages1: List[AnyMessage],
    ) -> AsyncIterable[str]: ...

    def write_response(
        self,
        *,
        request_id: str,
        response_messages: List[AnyMessage],
    ) -> StreamingResponse | JSONResponse:
        should_stream_response: Optional[bool] = self.stream

        if should_stream_response:
            stream_content: AsyncIterable[str] = self.stream_response(
                response_messages1=response_messages
            )
            return StreamingResponse(
                content=stream_content,
                media_type="text/event-stream",
            )
        else:
            chat_response = self.create_non_streaming_response(
                request_id=request_id,
                responses=response_messages,
                json_output_requested=False,
            )
            return JSONResponse(content=chat_response)

    @abstractmethod
    @property
    def instructions(self) -> Optional[str]: ...

    @abstractmethod
    @property
    def previous_response_id(self) -> Optional[str]: ...

    @abstractmethod
    @property
    def store(self) -> Optional[bool]: ...

    @abstractmethod
    @property
    def user_input(self) -> Optional[str]: ...

    @abstractmethod
    @property
    def metadata(self) -> Optional[dict[str, Any]]: ...
