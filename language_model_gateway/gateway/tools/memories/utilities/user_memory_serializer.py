import logging
from typing import Any


from language_model_gateway.gateway.tools.memories.structures.conversation_memory import (
    ConversationMemory,
)

logger = logging.getLogger(__name__)


class UserMemorySerializer:
    @staticmethod
    def serialize(memory: ConversationMemory) -> dict[str, Any]:
        return memory.model_dump()

    @staticmethod
    def deserialize(data: dict[str, Any]) -> ConversationMemory:
        return ConversationMemory(**data)
