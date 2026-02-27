import json
import logging
import time
from typing import AsyncIterator, Literal, cast, override, Any, List, Dict, Optional

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
    completion_create_params,
)
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionChunk,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice

from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.structures.openai.message.chat_completion_api_message_wrapper import (
    ChatCompletionApiMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.chat_message_helpers import (
    langchain_to_chat_message,
    convert_message_content_to_string,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ChatCompletionApiRequestWrapper(ChatRequestWrapper):
    def __init__(
        self, *, chat_request: ChatRequest, enable_debug_logging: bool
    ) -> None:
        """
        Wraps an OpenAI /chat/completions request to provide a consistent interface for different request types.

        """
        self.request: ChatRequest = chat_request

        self._messages: list[ChatMessageWrapper] = self.convert_from_chat_messages(
            messages=self.request.messages
        )

        self._enable_debug_logging: bool = enable_debug_logging

    @staticmethod
    def convert_from_chat_messages(
        *, messages: list[ChatCompletionMessageParam]
    ) -> list[ChatMessageWrapper]:
        return [ChatCompletionApiMessageWrapper(message=msg) for msg in messages]

    @override
    @property
    def model(self) -> str:
        return cast(str, self.request.model)

    @override
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
        return ChatCompletionApiMessageWrapper.create_system_message(content=content)

    @property
    @override
    def stream(self) -> Literal[False, True] | None | bool:
        return self.request.stream

    @property
    @override
    def response_format(self) -> Literal["text", "json_object", "json_schema"] | None:
        request_response_format = self.request.response_format
        # Convert NotGiven to None for type safety
        if request_response_format is None or isinstance(
            request_response_format, NotGiven
        ):
            response_format = None
        else:
            response_format = request_response_format
        if response_format is None:
            return None
        if isinstance(response_format, ResponseFormatJSONObject):
            if response_format.type == "json_object":
                return "json_object"
            elif response_format.type == "json_schema":
                return "json_schema"
            else:
                return "text"
        return "text"

    @property
    @override
    def response_json_schema(self) -> str | None:
        json_response_format: Optional[completion_create_params.ResponseFormat] = (
            self.request.response_format
        )
        if json_response_format is None:
            return None
        response_json_schema = json_response_format.get("json_schema")
        return str(response_json_schema) if response_json_schema else None

    @override
    def create_first_sse_message(self, *, request_id: str, source: str) -> str:
        raise NotImplementedError(
            "ChatCompletion API does not have a separate first SSE message.  The first message is created in the same format as subsequent messages with create_sse_message."
        )

    @override
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
        source: str,
    ) -> str:

        logger.debug(
            f"Creating SSE message with content: {content} from source: {source}"
        )
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
                        # content=f"[{source}]: {content}" if content else "",
                    ),
                )
            ]
            if content
            else [],
            usage=completion_usage_metadata,
            object="chat.completion.chunk",
        )
        return f"data: {chat_model_stream_response.model_dump_json()}\n\n"

    @override
    def create_debug_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
        source: str,
    ) -> str | None:
        return (
            self.create_sse_message(
                request_id=request_id,
                content=content,
                usage_metadata=usage_metadata,
                source=source,
            )
            if self._enable_debug_logging
            else None
        )

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
        self, *, request_id: str, usage_metadata: UsageMetadata | None, source: str
    ) -> str:
        logger.debug(f"Creating final SSE message from source: {source}")
        return "data: [DONE]\n\n"

    @override
    def to_dict(self) -> dict[str, Any]:
        """
        Returns a JSON-serializable dictionary representation of the request wrapper.
        """
        return {
            "model": self.model,
            "messages": [
                m.to_dict() if hasattr(m, "to_dict") else str(m) for m in self._messages
            ],
            "stream": self.stream,
            "response_format": self.response_format,
            "response_json_schema": self.response_json_schema,
            "request": self.request.model_dump()
            if hasattr(self.request, "model_dump")
            else str(self.request),
        }

    @override
    def stream_response(
        self,
        *,
        response_messages1: List[AnyMessage],
    ) -> AsyncIterator[str]:
        """Streams the response messages as Server-Sent Events (SSE) in the OpenAI format."""

        async def response_stream() -> AsyncIterator[str]:
            for response_message in response_messages1:
                message_content: str = convert_message_content_to_string(
                    response_message.content
                )
                if message_content:
                    chat_stream_response: ChatCompletionChunk = ChatCompletionChunk(
                        id="1",
                        created=int(time.time()),
                        model=self.model,
                        choices=[
                            ChunkChoice(
                                index=0,
                                delta=ChoiceDelta(
                                    role="assistant",
                                    content=message_content + "\n",
                                ),
                            )
                        ],
                        usage=CompletionUsage(
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                        ),
                        object="chat.completion.chunk",
                    )
                    yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"
            yield "data: [DONE]\n\n"

        return response_stream()

    @override
    @property
    def instructions(self) -> Optional[str]:
        """ChatCompletion API does not have a separate instructions field, so we return None."""
        return None

    @override
    @property
    def previous_response_id(self) -> Optional[str]:
        """ChatCompletion API does not have a separate previous_response_id field, so we return None."""
        return None

    @override
    @property
    def store(self) -> Optional[bool]:
        """ChatCompletion API does not have a separate store field, so we return None."""
        return None

    @override
    @property
    def user_input(self) -> Optional[str]:
        """Extract the user input from the messages. We assume the user input is the content of the last message with role 'user'."""
        for message in reversed(self._messages):
            if message.role == "user":
                return message.content
        return None

    @override
    @property
    def metadata(self) -> Optional[dict[str, Any]]:
        """Responses API does have a metadata field."""
        return self.request.metadata

    @override
    @property
    def max_tokens(self) -> Optional[int]:
        """Return the max_tokens parameter from the request, which is used in both ChatCompletion and Responses API."""
        return self.request.max_tokens

    @override
    @property
    def max_output_tokens(self) -> Optional[int]:
        """Return the max_output_tokens parameter from the request, which is used in both ChatCompletion and Responses API."""
        return self.request.max_completion_tokens

    @override
    @property
    def temperature(self) -> Optional[float]:
        """Return the temperature parameter from the request, which is used in both ChatCompletion and Responses API."""
        return self.request.temperature

    @override
    @property
    def enable_debug_logging(self) -> bool:
        """Return whether debug logging is enabled for this request."""
        return self._enable_debug_logging
