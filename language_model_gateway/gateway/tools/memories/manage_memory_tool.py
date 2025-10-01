import logging
import typing
from typing import Annotated, Literal, Type, List

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore, SearchItem
from langmem import errors
from langmem.utils import NamespaceTemplate
from pydantic import BaseModel, Field

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.structures.conversation_memory import (
    ConversationMemory,
)
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class ConversationMemoryInput(BaseModel):
    action: Literal["create", "update", "delete", "search"] = Field(
        description="Action to perform on the user profile (create, update, delete, or search)"
    )
    state: Annotated[MyMessagesState, InjectedState] = Field()
    memory: typing.Optional[ConversationMemory] = Field(
        default=None,
        description="The memory data to create or update. Required for create/update. Omit for search/delete unless needed.",
    )
    query: typing.Optional[str] = Field(
        default=None,
        description="Query string to search for relevant memories. Only used for search action.",
    )


class ManageMemoryTool(ResilientBaseTool):
    """
    Tool for managing persistent memories in conversations. Supports create, update, and delete actions.

    Use this tool to store, search, update, or delete a memory for this conversation.
    Use it whenever you need to remember something, retrieve a memory, update, or delete it.
    Actions: 'create' (store new memory), 'search' (find memories by query),
    'update' (modify existing memory, include MEMORY ID), 'delete' (remove memory, include MEMORY ID).

    Examples:
    - To remember something: action='create', memory=...
    - To search: action='search', query='...'
    - To update: action='update', memory=..., include MEMORY ID
    - To delete: action='delete', memory=..., include MEMORY ID

    Call this tool whenever a user asks to remember, search, update, or delete a memory,
    or when you want to proactively store or retrieve context that may be important for the conversation,
    such as general disclosures, health information, or any information that could be useful later—even if the user does not explicitly request it.
    """

    name: str = "manage_memory"
    description: str = (
        "Store, search, update, or delete a memory for this conversation. "
        "Use this tool whenever you need to remember something, retrieve a memory, update, or delete it. "
        "Actions: 'create' (store new memory), 'search' (find memories by query), "
        "'update' (modify existing memory, include MEMORY ID), 'delete' (remove memory, include MEMORY ID). "
        "Examples: "
        "- To remember something: action='create', memory=... "
        "- To search: action='search', query='...' "
        "- To update: action='update', memory=..., include MEMORY ID "
        "- To delete: action='delete', memory=..., include MEMORY ID "
        "Call this tool whenever a user asks to remember, search, update, or delete a memory, "
        "or when you want to proactively store or retrieve context that may be important for the conversation, "
        "such as general disclosures, health information, or any information that could be useful later—even if the user does not explicitly request it."
    )
    namespace: tuple[str, ...] | str
    args_schema: Type[BaseModel] = ConversationMemoryInput
    actions_permitted: typing.Optional[
        tuple[typing.Literal["create", "update", "delete", "search"], ...]
    ] = ("create", "update", "delete", "search")
    store: typing.Optional[BaseStore] = None

    def _run(
        self,
        *,
        memory: ConversationMemory,
        action: str | None = None,
        state: Annotated[MyMessagesState, InjectedState],
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        *,
        memory: typing.Optional[ConversationMemory] = None,
        action: str | None = None,
        state: Annotated[MyMessagesState, InjectedState],
        query: typing.Optional[str] = None,
    ) -> str:
        if self.actions_permitted and action not in self.actions_permitted:
            raise ToolException(
                f"Invalid action {action}. Must be one of {self.actions_permitted}."
            )
        try:
            if not state.user_id:
                raise ToolException(
                    "user_id is required in the state to store user profile"
                )
            store = self._get_store()
            namespacer = NamespaceTemplate(self.namespace)
            namespace = namespacer()
            key: str = f"user_profile_{state.user_id}"
            if action == "delete":
                await store.adelete(namespace, key=str(key))
                return f"Deleted user profile {key}"
            if action == "search":
                # For demonstration, return all memories for the user, or filter by query if provided
                all_memories: List[SearchItem] = await store.asearch(namespace)
                user_memories = [m for m in all_memories]
                if query:
                    user_memories = [
                        m for m in user_memories if query.lower() in str(m).lower()
                    ]
                return f"Found {len(user_memories)} memories: {user_memories}"
            if not memory:
                raise ToolException("memory is required for create/update actions")
            memory_copy = memory.model_copy()
            memory_copy.user_id = state.user_id
            await store.aput(
                namespace,
                key=str(key),
                value=self._ensure_json_serializable(memory_copy),
            )
            return f"{action}d memory {key}"
        except Exception as e:
            logger.exception("Error storing user profile")
            raise ToolException("Error storing user profile") from e

    def _get_store(self) -> BaseStore:
        if self.store is not None:
            return self.store
        try:
            return get_store()
        except RuntimeError as e:
            raise errors.ConfigurationError("Could not get store") from e

    @staticmethod
    def _ensure_json_serializable(content: typing.Any) -> typing.Any:
        if isinstance(content, (str, int, float, bool, dict, list)):
            return content
        if hasattr(content, "model_dump"):
            try:
                return content.model_dump(mode="json")
            except Exception as e:
                logger.error(e)
                return str(content)
        return content
