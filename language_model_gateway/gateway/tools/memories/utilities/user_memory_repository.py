import logging

from langgraph.store.base import BaseStore
from langmem.utils import NamespaceTemplate

from language_model_gateway.gateway.tools.memories.structures.conversation_memory import (
    ConversationMemory,
)
from language_model_gateway.gateway.tools.memories.utilities.user_memory_serializer import (
    UserMemorySerializer,
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
