from typing import Optional, cast, override

from langchain_core.messages import BaseMessage
from openai.types.responses import ResponseInputItemParam, EasyInputMessageParam

from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
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
        raise ValueError(
            "Cannot convert Responses API message to LangChain message directly."
            " Use from_chat_completion_message_to_langchain_message instead."
        )
