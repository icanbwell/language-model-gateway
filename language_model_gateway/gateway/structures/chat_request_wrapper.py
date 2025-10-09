from typing import Literal, cast, Union

from openai import NotGiven
from openai.types import ResponseFormatJSONObject
from openai.types.chat.completion_create_params import ResponseFormat

from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.schema.openai.responses import ResponsesRequest
from language_model_gateway.gateway.structures.chat_completion_message_wrapper import (
    ChatCompletionMessageWrapper,
)
from language_model_gateway.gateway.structures.chat_message_wrapper import (
    ChatMessageWrapper,
)
from openai.types.chat import (
    ChatCompletionMessageParam,
)
from openai.types.responses import (
    ResponseInputParam,
    EasyInputMessageParam,
)

from language_model_gateway.gateway.structures.responses_message_wrapper import (
    ResponsesMessageWrapper,
)


class ChatRequestWrapper:
    def __init__(self, chat_request: ChatRequest | ResponsesRequest) -> None:
        """
        Wraps either a ChatRequest or ResponsesRequest and provides a unified interface so the code can use either

        """
        self.request: ChatRequest | ResponsesRequest = chat_request

        self._messages: list[ChatMessageWrapper] = (
            self.convert_from_responses_input(input_=self.request.input)
            if isinstance(self.request, ResponsesRequest)
            else self.convert_from_chat_messages(messages=self.request.messages)
        )

    @staticmethod
    def convert_from_chat_messages(
        *, messages: list[ChatCompletionMessageParam]
    ) -> list[ChatMessageWrapper]:
        return [ChatCompletionMessageWrapper(message=msg) for msg in messages]

    @staticmethod
    def convert_from_responses_input(
        *, input_: Union[str, ResponseInputParam]
    ) -> list[ChatMessageWrapper]:
        if isinstance(input_, str):
            return [
                ResponsesMessageWrapper(
                    input_=EasyInputMessageParam(role="user", content=input_)
                )
            ]
        elif isinstance(input_, list):
            return [ResponsesMessageWrapper(input_=item) for item in input_]
        else:
            return []

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
            ResponsesMessageWrapper.create_system_message(content=content)
            if isinstance(self.request, ResponsesRequest)
            else ChatCompletionMessageWrapper.create_system_message(content=content)
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
