from typing import Optional, cast, override, Literal

from langchain_core.messages import BaseMessage
from openai.types.chat import ChatCompletionMessageParam
from openai.types.responses import ResponseInputItemParam, EasyInputMessageParam

from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.utilities.openai.responses_api_converter import (
    convert_responses_api_to_single_message,
)


class ResponsesApiMessageWrapper(ChatMessageWrapper):
    def __init__(self, *, input_: ResponseInputItemParam) -> None:
        """
        Wraps a message from the OpenAI /responses API and provides a unified interface so the code can use either one.

        """
        self.input_: ResponseInputItemParam = input_

    @classmethod
    def create_system_message(cls, *, content: str) -> "ResponsesApiMessageWrapper":
        return cls(input_=EasyInputMessageParam(role="system", content=content))

    @override
    @property
    def system_message(self) -> bool:
        # Use getattr with default to avoid mypy union-attr error
        role = getattr(self.input_, "role", None)
        if role is not None:
            return True if role == "system" else False
        elif isinstance(self.input_, dict):
            return self.input_.get("role") == "system"
        return False

    @override
    @property
    def content(self) -> str | None:
        # Use getattr with default to avoid mypy union-attr error
        content = getattr(self.input_, "content", None)
        if content is not None:
            return cast(Optional[str], content)
        elif isinstance(self.input_, dict):
            return cast(Optional[str], self.input_.get("content"))
        return None

    @override
    def to_langchain_message(self) -> BaseMessage:
        # Use the correct conversion for ResponsesApiMessageWrapper
        return convert_responses_api_to_single_message(response=self.input_)

    @override
    def to_chat_completion_message(self) -> ChatCompletionMessageParam:
        """Convert the message wrapper back to a ChatCompletionMessageParam, which is the same format as the original message.  This is used for tools that need to send messages back to the model in the same format as the original messages."""
        raise NotImplementedError(
            "Conversion from ResponsesApiMessageWrapper to ChatCompletionMessageParam is not implemented yet."
        )

    @override
    def to_responses_api_message(self) -> ResponseInputItemParam:
        return self.input_

    @override
    @property
    def role(self) -> Literal["system", "user", "assistant"] | None:
        # Use getattr with default to avoid mypy union-attr error
        role = getattr(self.input_, "role", None)
        if role is not None:
            return cast(Optional[Literal["system", "user", "assistant"]], role)
        elif isinstance(self.input_, dict):
            return cast(
                Optional[Literal["system", "user", "assistant"]],
                self.input_.get("role"),
            )
        return None
