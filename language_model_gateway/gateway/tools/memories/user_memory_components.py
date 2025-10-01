import logging
from typing import Any, Optional

from langchain_core.tools import ToolException
from langgraph.store.base import BaseStore
from langmem.utils import NamespaceTemplate

from language_model_gateway.gateway.structures.conversation_memory import (
    ConversationMemory,
)

logger = logging.getLogger(__name__)


class UserMemoryRepository:
    def __init__(self, store: BaseStore, namespace: str | tuple[str, ...]):
        self.store = store
        self.namespace = NamespaceTemplate(namespace)()

    async def save(self, memory: ConversationMemory) -> None:
        memory_id = f"user_memory_{memory.user_id}_{memory.conversation_id}"
        await self.store.aput(
            self.namespace,
            key=memory_id,
            value=UserMemorySerializer.serialize(memory),
        )

    async def delete(self, user_id: str, conversation_id: str) -> None:
        memory_id = f"user_memory_{user_id}_{conversation_id}"
        await self.store.adelete(self.namespace, key=memory_id)


class UserMemoryValidator:
    @staticmethod
    def validate_action(
        action: str | None, permitted: Optional[tuple[str, ...]] = None
    ) -> None:
        if not action:
            raise ToolException("Action is required")
        if permitted and action not in permitted:
            raise ToolException(f"Invalid action {action}. Must be one of {permitted}.")

    @staticmethod
    def validate_state_user_id(state: Any) -> None:
        if not getattr(state, "user_id", None):
            raise ToolException("user_id is required in the state to store user memory")
        if not getattr(state, "conversation_id", None):
            raise ToolException(
                "conversation_id is required in the state to store user memory"
            )


class UserMemorySerializer:
    @staticmethod
    def serialize(memory: ConversationMemory) -> dict[str, Any]:
        return memory.model_dump()

    @staticmethod
    def deserialize(data: dict[str, Any]) -> ConversationMemory:
        return ConversationMemory(**data)
