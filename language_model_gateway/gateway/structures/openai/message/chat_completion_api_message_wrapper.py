from typing import Optional, cast, override, Literal

from langchain_community.adapters.openai import convert_dict_to_message
from langchain_core.messages import BaseMessage
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
)
from openai.types.responses.response_input_param import ResponseInputItemParam

from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)


class ChatCompletionApiMessageWrapper(ChatMessageWrapper):
    def __init__(self, *, message: ChatCompletionMessageParam) -> None:
        """
        Wraps a chat message from the OpenAI /chat/completion API and provides a unified interface so the code can use either chat completion API messages or other message types.

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
        return self.role == "system"

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

    @override
    def to_chat_completion_message(self) -> ChatCompletionMessageParam:
        """Convert the message wrapper back to a ChatCompletionMessageParam, which is the same format as the original message.  This is used for tools that need to send messages back to the model in the same format as the original messages."""
        return self.message

    @override
    def to_responses_api_message(self) -> ResponseInputItemParam:
        raise NotImplementedError(
            "Conversion from ChatCompletionMessageParam to EasyInputMessageParam is not implemented."
        )

    @override
    @property
    def role(self) -> Literal["system", "user", "assistant"] | None:
        role = getattr(self.message, "role", None)
        if role is not None:
            return cast(Literal["system", "user", "assistant"], role)
        elif isinstance(self.message, dict):
            return cast(
                Literal["system", "user", "assistant"], self.message.get("role")
            )
        else:
            return None
