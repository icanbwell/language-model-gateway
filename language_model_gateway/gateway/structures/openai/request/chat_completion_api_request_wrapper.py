import json
import time
from typing import Literal, cast, override, Any, List, Dict, Optional

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolMessage,
)
from langchain_core.messages.ai import UsageMetadata
from openai import NotGiven
from openai.types import ResponseFormatJSONObject, CompletionUsage
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
)
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionChunk,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice
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
from language_model_gateway.gateway.utilities.chat_message_helpers import (
    langchain_to_chat_message,
)
from language_model_gateway.gateway.utilities.json_extractor import JsonExtractor


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

    @override
    @property
    def model(self) -> str:
        return cast(str, self.request.model)

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
        return (
            ResponsesApiMessageWrapper.create_system_message(content=content)
            if isinstance(self.request, ResponsesRequest)
            else ChatCompletionApiMessageWrapper.create_system_message(content=content)
        )

    @override
    @property
    def stream(self) -> Literal[False, True] | None | bool:
        return self.request.stream

    @override
    @property
    def response_format(self) -> ResponseFormat | NotGiven:
        return cast(
            ResponseFormat,
            ResponseFormatJSONObject  # in case of ResponsesRequest, we always use JSON object format
            if isinstance(self.request, ResponsesRequest)
            else self.request.response_format,
        )

    @override
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
    ) -> str:
        completion_usage_metadata: CompletionUsage | None = (
            (self.convert_usage_meta_data_to_openai(usages=[usage_metadata]))
            if usage_metadata
            else None
        )

        chat_model_stream_response: ChatCompletionChunk = ChatCompletionChunk(
            id=request_id,
            created=int(time.time()),
            model=self.model,
            choices=[
                ChunkChoice(
                    index=0,
                    delta=ChoiceDelta(
                        role="assistant",
                        content=content,
                    ),
                )
            ]
            if content
            else [],
            usage=completion_usage_metadata,
            object="chat.completion.chunk",
        )
        return f"data: {json.dumps(chat_model_stream_response.model_dump())}\n\n"

    @override
    def create_non_streaming_response(
        self,
        *,
        request_id: str,
        json_output_requested: Optional[bool],
        responses: List[AnyMessage],
    ) -> dict[str, Any]:
        # add usage metadata from each message into a total usage metadata
        total_usage_metadata: CompletionUsage = self.convert_usage_meta_data_to_openai(
            usages=[
                m.usage_metadata
                for m in responses
                if hasattr(m, "usage_metadata") and m.usage_metadata
            ]
        )

        output_messages_raw: List[ChatCompletionMessage | None] = [
            langchain_to_chat_message(m)
            for m in responses
            if isinstance(m, AIMessage) or isinstance(m, ToolMessage)
        ]
        output_messages: List[ChatCompletionMessage] = [
            m for m in output_messages_raw if m is not None
        ]

        choices: List[Choice] = [
            Choice(index=i, message=m, finish_reason="stop")
            for i, m in enumerate(output_messages)
        ]

        choices_text = "\n".join([f"{c.message.content}" for c in choices])

        if json_output_requested:
            # extract the json content from response and just return that
            json_content_raw: Dict[str, Any] | List[Dict[str, Any]] | str = (
                (JsonExtractor.extract_structured_output(text=choices_text))
                if choices_text
                else choices_text
            )
            json_content: str = json.dumps(json_content_raw)
            choices = [
                Choice(
                    index=i,
                    message=ChatCompletionMessage(
                        content=json_content, role="assistant"
                    ),
                    finish_reason="stop",
                )
                for i in range(1)
            ]

        chat_response: ChatCompletion = ChatCompletion(
            id=request_id,
            model=self.model,
            choices=choices,
            usage=total_usage_metadata,
            created=int(time.time()),
            object="chat.completion",
        )
        content_json: Dict[str, Any] = chat_response.model_dump()
        return content_json

    # noinspection PyMethodMayBeStatic
    def convert_usage_meta_data_to_openai(
        self, *, usages: List[UsageMetadata]
    ) -> CompletionUsage:
        total_usage_metadata: CompletionUsage = CompletionUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
        usage_metadata: UsageMetadata
        for usage_metadata in usages:
            total_usage_metadata.prompt_tokens += usage_metadata["input_tokens"]
            total_usage_metadata.completion_tokens += usage_metadata["output_tokens"]
            total_usage_metadata.total_tokens += usage_metadata["total_tokens"]
        return total_usage_metadata

    @override
    def create_final_sse_message(
        self, *, request_id: str, usage_metadata: UsageMetadata | None
    ) -> str:
        return "data: [DONE]\n\n"
