from typing import Literal, Union, override, Optional, List, Any
import json

from langchain_core.messages import AnyMessage
from langchain_core.messages.ai import UsageMetadata
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

    @property
    @override
    def model(self) -> str:
        return self.request.model

    @property  # type: ignore[explicit-override]
    @override
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
    def response_format(self) -> Literal["text", "json_object", "json_schema"] | None:
        return "json_object"  # in case of ResponsesRequest, we always use JSON object format

    @override
    @property
    def response_json_schema(self) -> str | None:
        return None  # Not applicable for ResponsesRequest

    @override
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
    ) -> str:
        # Format a single SSE message chunk for streaming
        if content is None:
            return ""
        message: dict[str, Any] = {
            "id": request_id,
            "object": "response.chunk",
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": None,
                }
            ],
        }
        if usage_metadata:
            message["usage"] = dict(usage_metadata)
        return f"data: {json.dumps(message)}\n\n"

    @override
    def create_final_sse_message(
        self, *, request_id: str, usage_metadata: UsageMetadata | None
    ) -> str:
        # Format the final SSE message chunk
        message: dict[str, Any] = {
            "id": request_id,
            "object": "response",
            "model": self.model,
            "choices": [],
        }
        if usage_metadata:
            message["usage"] = dict(usage_metadata)
        return f"data: {json.dumps(message)}\n\n"

    @override
    def create_non_streaming_response(
        self,
        *,
        request_id: str,
        json_output_requested: Optional[bool],
        responses: List[AnyMessage],
    ) -> dict[str, Any]:
        # Build a non-streaming response dict
        choices = []
        for idx, msg in enumerate(responses):
            content = getattr(msg, "content", None)
            choices.append(
                {
                    "index": idx,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": None,
                }
            )
        response = {
            "id": request_id,
            "object": "response",
            "model": self.model,
            "choices": choices,
        }
        # Usage metadata is not passed here, but could be added if available
        return response

    @override
    def to_dict(self) -> dict[str, Any]:
        return self.request.model_dump(mode="json")
