import logging
import uuid
from typing import Type, Optional, Any, Literal

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.store.base import BaseStore
from langmem import errors
from langmem.utils import NamespaceTemplate
from pydantic import BaseModel

from language_model_gateway.gateway.structures.conversation_memory import (
    ConversationMemory,
)
from language_model_gateway.gateway.tools.memories.conversation_memory_write_input import (
    ConversationMemoryWriteInput,
)
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class MemoryWriteTool(ResilientBaseTool):
    """
    Tool for creating and deleting persistent memories in conversations.
    Actions: 'create' (store new memory), 'delete' (remove memory, include MEMORY ID).
    """

    name: str = "memory_writer"
    description: str = (
        "Store, update, or delete a memory for this conversation. "
        "Use this tool whenever you need to remember something, update a memory, or delete it. "
        "Actions: 'create' (store new memory) "
        "'update' (modify existing memory, include MEMORY ID), 'delete' (remove memory, include MEMORY ID). "
        "Examples: "
        "- To remember something: action='create', memory=... "
        "- To update: action='update', memory=..., include MEMORY ID "
        "- To delete: action='delete', memory=..., include MEMORY ID "
        "Call this tool whenever a user asks to remember, update, or delete a memory, "
        "or when you want to proactively store or retrieve context that may be important for the conversation"
        " or user profile, "
        "such as general disclosures, health information (e.g., diabetes), user profile data, or any information that"
        " could be useful later—even if the user does not explicitly request it. "
        "This tool is appropriate for storing both conversational context and important user profile information"
        " that may be relevant in future interactions."
    )
    namespace: tuple[str, ...] | str = ("memories", "{user_id}", "memories")
    args_schema: Type[BaseModel] = ConversationMemoryWriteInput
    actions_permitted: Optional[tuple[Literal["create", "update", "delete"], ...]] = (
        "create",
        "update",
        "delete",
    )
    store: Optional[BaseStore] = None

    def _run(
        self,
        *,
        memory: Optional[ConversationMemory] = None,
        action: Literal["create", "update", "delete", "search"] | None = None,
        user_id: str,
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        *,
        memory: Optional[ConversationMemory] = None,
        action: Literal["create", "update", "delete", "search"] | None = None,
        user_id: str,
    ) -> str:
        logger.info(
            f"{self.__class__.__name__} _arun: memory={memory.model_dump() if memory else None}, action={action}"
        )
        if self.actions_permitted and action not in self.actions_permitted:
            raise ToolException(
                f"Invalid action {action}. Must be one of {self.actions_permitted}."
            )
        if not user_id:
            raise ToolException("user_id is required for memory operations")
        store = self._get_store(store=self.store)
        namespacer = NamespaceTemplate(self.namespace)
        namespace = namespacer()
        if action == "delete":
            if not memory or not memory.memory_id:
                raise ToolException("memory and memory_id required for delete")
            key = f"memory_{memory.memory_id}"
            await store.adelete(namespace, key=key)
            return f"Deleted memory {key}"
        elif action == "create":
            if not memory:
                raise ToolException("memory is required for create")
            if not memory.memory_id:
                memory.memory_id = str(uuid.uuid4())
            key = f"memory_{memory.memory_id}"
            memory_copy: ConversationMemory = memory.model_copy()
            await store.aput(
                namespace,
                key=key,
                value=self._ensure_json_serializable(content=memory_copy),
            )
            return f"Created memory {key}:\n{'\n'.join(memory_copy.recent_memories)}"
        else:
            raise ToolException("Unsupported action for MemoryWriteTool")

    @staticmethod
    def _get_store(*, store: BaseStore | None = None) -> BaseStore:
        if store is not None:
            return store
        try:
            return get_store()
        except RuntimeError as e:
            raise errors.ConfigurationError("Could not get store") from e

    @staticmethod
    def _ensure_json_serializable(*, content: Any) -> Any:
        if isinstance(content, (str, int, float, bool, dict, list)):
            return content
        if hasattr(content, "model_dump"):
            try:
                return content.model_dump(mode="json")
            except Exception as e:
                logger.error(e)
                return str(content)
        return content
