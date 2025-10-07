import typing
from typing import Literal

from pydantic import BaseModel, Field

from language_model_gateway.gateway.structures.conversation_memory import (
    ConversationMemory,
)


class ConversationMemoryWriteInput(BaseModel):
    action: Literal["create", "delete", "update"] = Field(
        description="Action to perform on the memory (create, delete, or update)"
    )
    memory: typing.Optional[ConversationMemory] = Field(
        default=None,
        description="The memory data to create or delete or update.  For delete, only the id field is required.",
    )
    user_id: str = Field(
        description="User ID associated with the memory. Required for create/delete actions.",
    )
