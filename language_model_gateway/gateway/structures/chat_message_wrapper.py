from typing import Optional, cast

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
)
from openai.types.responses import ResponseInputItemParam


class ChatMessageWrapper:
    def __init__(
        self, *, message_or_input: ChatCompletionMessageParam | ResponseInputItemParam
    ) -> None:
        """
        Wraps either a ChatMessage or a ChatCompletionInputMessage and provides a unified interface so the code can use either

        """
        self.message_or_input: ChatCompletionMessageParam | ResponseInputItemParam = (
            message_or_input
        )

    @classmethod
    def create_system_message(cls, *, content: str) -> "ChatMessageWrapper":
        return cls(
            message_or_input=ChatCompletionSystemMessageParam(
                role="system", content=content
            )
        )

    @property
    def system_message(self) -> bool:
        # Use getattr with default to avoid mypy union-attr error
        role = getattr(self.message_or_input, "role", None)
        if role is not None:
            return True if role == "system" else False
        elif isinstance(self.message_or_input, dict):
            return self.message_or_input.get("role") == "system"
        return False

    @property
    def content(self) -> str | None:
        # Use getattr with default to avoid mypy union-attr error
        content = getattr(self.message_or_input, "content", None)
        if content is not None:
            return cast(Optional[str], content)
        elif isinstance(self.message_or_input, dict):
            return cast(Optional[str], self.message_or_input.get("content"))
        return None
