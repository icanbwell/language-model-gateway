from typing import Optional, cast

from langchain_community.adapters.openai import convert_dict_to_message
from langchain_core.messages import BaseMessage
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
)

from language_model_gateway.gateway.structures.chat_message_wrapper import (
    ChatMessageWrapper,
)


class ChatCompletionMessageWrapper(ChatMessageWrapper):
    def __init__(self, *, message: ChatCompletionMessageParam) -> None:
        """
        Wraps either a ChatMessage or a ChatCompletionInputMessage and provides a unified interface so the code can use either

        """
        self.message: ChatCompletionMessageParam = message

    @classmethod
    def create_system_message(cls, *, content: str) -> "ChatCompletionMessageWrapper":
        return cls(
            message=ChatCompletionSystemMessageParam(role="system", content=content)
        )

    @property
    def system_message(self) -> bool:
        # Use getattr with default to avoid mypy union-attr error
        role = getattr(self.message, "role", None)
        if role is not None:
            return True if role == "system" else False
        elif isinstance(self.message, dict):
            return self.message.get("role") == "system"
        return False

    @property
    def content(self) -> str | None:
        # Use getattr with default to avoid mypy union-attr error
        content = getattr(self.message, "content", None)
        if content is not None:
            return cast(Optional[str], content)
        elif isinstance(self.message, dict):
            return cast(Optional[str], self.message.get("content"))
        return None

    def to_langchain_message(self) -> BaseMessage:
        return self.from_chat_completion_message_to_langchain_message(
            message=self.message
        )

    @staticmethod
    def from_chat_completion_message_to_langchain_message(
        message: ChatCompletionMessageParam,
    ) -> BaseMessage:
        return convert_dict_to_message(message)
