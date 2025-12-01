from typing import Optional, cast, override

from langchain_community.adapters.openai import convert_dict_to_message
from langchain_core.messages import BaseMessage
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
)

from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)


class ChatCompletionApiMessageWrapper(ChatMessageWrapper):
    def __init__(self, *, message: ChatCompletionMessageParam) -> None:
        """
        Wraps a chat message from the OpenAI /chat/completion API and provides a unified interface so the code can use either

        """
        self.message: ChatCompletionMessageParam = message

    @classmethod
    def create_system_message(
        cls, *, content: str
    ) -> "ChatCompletionApiMessageWrapper":
        return cls(
            message=ChatCompletionSystemMessageParam(role="system", content=content)
        )

    @override
    @property
    def system_message(self) -> bool:
        # Use getattr with default to avoid mypy union-attr error
        role = getattr(self.message, "role", None)
        if role is not None:
            return True if role == "system" else False
        elif isinstance(self.message, dict):
            return self.message.get("role") == "system"
        return False

    @override
    @property
    def content(self) -> str | None:
        # Use getattr with default to avoid mypy union-attr error
        content = getattr(self.message, "content", None)
        if content is not None:
            return cast(Optional[str], content)
        elif isinstance(self.message, dict):
            return cast(Optional[str], self.message.get("content"))
        return None

    @override
    def to_langchain_message(self) -> BaseMessage:
        return self.from_chat_completion_message_to_langchain_message(
            message=self.message
        )

    @staticmethod
    def from_chat_completion_message_to_langchain_message(
        message: ChatCompletionMessageParam,
    ) -> BaseMessage:
        # call the utility function in langchain_community.adapters.openai to convert dict to langchain message
        return convert_dict_to_message(message)
