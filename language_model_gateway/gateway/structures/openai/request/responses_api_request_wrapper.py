from typing import Literal, Union, override

from openai import NotGiven
from openai.types import CompletionUsage
from openai.types.shared_params.response_format_json_object import (
    ResponseFormatJSONObject,
)
from openai.types.chat.completion_create_params import ResponseFormat
from openai.types.responses import (
    ResponseInputParam,
    EasyInputMessageParam,
)

from language_model_gateway.gateway.schema.openai.responses import ResponsesRequest
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.message.responses_api_message_wrapper import (
    ResponsesApiMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)


class ResponsesApiRequestWrapper(ChatRequestWrapper):
    def __init__(self, chat_request: ResponsesRequest) -> None:
        """
        Wraps an OpenAI /responses API request and provides a unified interface so the code can use it

        """
        self.request: ResponsesRequest = chat_request

        self._messages: list[ChatMessageWrapper] = self.convert_from_responses_input(
            input_=self.request.input
        )

    @staticmethod
    def convert_from_responses_input(
        *, input_: Union[str, ResponseInputParam]
    ) -> list[ChatMessageWrapper]:
        if isinstance(input_, str):
            return [
                ResponsesApiMessageWrapper(
                    input_=EasyInputMessageParam(role="user", content=input_)
                )
            ]
        elif isinstance(input_, list):
            return [ResponsesApiMessageWrapper(input_=item) for item in input_]
        else:
            return []

    @override
    @property
    def model(self) -> str:
        return self.request.model

    @property
    def messages(self) -> list[ChatMessageWrapper]:
        return self._messages

    @messages.setter
    def messages(self, value: list[ChatMessageWrapper]) -> None:
        self._messages = value

    @override
    def append_message(self, *, message: ChatMessageWrapper) -> None:
        self._messages.append(message)

    @override
    def create_system_message(self, *, content: str) -> ChatMessageWrapper:
        return ResponsesApiMessageWrapper.create_system_message(content=content)

    @override
    @property
    def stream(self) -> Literal[False, True] | None | bool:
        return self.request.stream

    @override
    @property
    def response_format(self) -> ResponseFormat | NotGiven:
        return ResponseFormatJSONObject(
            type="json_object"
        )  # in case of ResponsesRequest, we always use JSON object format

    @override
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        completion_usage_metadata: CompletionUsage,
    ) -> str:
        return "data: TODO: \n\n"
