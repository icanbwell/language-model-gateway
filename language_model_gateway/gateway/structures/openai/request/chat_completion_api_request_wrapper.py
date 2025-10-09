from typing import Literal, cast

from openai import NotGiven
from openai.types import ResponseFormatJSONObject
from openai.types.chat import (
    ChatCompletionMessageParam,
)
from openai.types.chat.completion_create_params import ResponseFormat

from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.schema.openai.responses import ResponsesRequest
from language_model_gateway.gateway.structures.openai.message.chat_completion_api_message_wrapper import (
    ChatCompletionApiMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.message.responses_api_message_wrapper import (
    ResponsesApiMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)


class ChatCompletionApiRequestWrapper(ChatRequestWrapper):
    def __init__(self, chat_request: ChatRequest) -> None:
        """
        Wraps an OpenAI /chat/completions request to provide a consistent interface for different request types.

        """
        self.request: ChatRequest = chat_request

        self._messages: list[ChatMessageWrapper] = self.convert_from_chat_messages(
            messages=self.request.messages
        )

    @staticmethod
    def convert_from_chat_messages(
        *, messages: list[ChatCompletionMessageParam]
    ) -> list[ChatMessageWrapper]:
        return [ChatCompletionApiMessageWrapper(message=msg) for msg in messages]

    @property
    def model(self) -> str:
        return cast(str, self.request.model)

    @property
    def messages(self) -> list[ChatMessageWrapper]:
        return self._messages

    @messages.setter
    def messages(self, value: list[ChatMessageWrapper]) -> None:
        self._messages = value

    def append_message(self, *, message: ChatMessageWrapper) -> None:
        self._messages.append(message)

    def create_system_message(self, *, content: str) -> ChatMessageWrapper:
        return (
            ResponsesApiMessageWrapper.create_system_message(content=content)
            if isinstance(self.request, ResponsesRequest)
            else ChatCompletionApiMessageWrapper.create_system_message(content=content)
        )

    @property
    def stream(self) -> Literal[False, True] | None | bool:
        return self.request.stream

    @property
    def response_format(self) -> ResponseFormat | NotGiven:
        return cast(
            ResponseFormat,
            ResponseFormatJSONObject  # in case of ResponsesRequest, we always use JSON object format
            if isinstance(self.request, ResponsesRequest)
            else self.request.response_format,
        )
