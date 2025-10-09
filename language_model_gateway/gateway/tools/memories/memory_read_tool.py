import logging
import typing
from typing import Type, List, Optional, Literal, Dict, Any

from langgraph.config import get_store
from langgraph.store.base import BaseStore, SearchItem
from langmem import errors
from langmem.utils import NamespaceTemplate
from pydantic import BaseModel

from language_model_gateway.gateway.tools.memories.structures.conversation_memory import (
    ConversationMemory,
)
from language_model_gateway.gateway.tools.memories.structures.conversation_memory_read_input import (
    ConversationMemoryReadInput,
)
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class MemoryReadTool(ResilientBaseTool):
    """
    Tool for retrieving persistent memories in conversations.
    Action: 'search' (find memories by query or get all for user).
    """

    name: str = "memory_reader"
    description: str = (
        "Search a memory for this conversation. "
        "Use this tool whenever you need to retrieve a memory. "
        "Actions: 'search' (find memories by query), "
        "Examples: "
        "- To search: action='search', query='...' "
        "Call this tool whenever a user asks to search for a memory, "
        "or when you want to proactively store or retrieve context that may be important for the conversation or user profile, "
        "such as general disclosures, health information (e.g., diabetes), user profile data, or any information"
        " that could be useful later—even if the user does not explicitly request it. "
        "This tool is appropriate for storing both conversational context and important user profile information"
        " that may be relevant in future interactions."
    )
    namespace: tuple[str, ...] | str = ("memories", "{user_id}", "memories")
    args_schema: Type[BaseModel] = ConversationMemoryReadInput
    actions_permitted: Optional[tuple[Literal["search"], ...]] = ("search",)
    store: Optional[BaseStore] = None

    def _run(
        self,
        *,
        all_memories: Optional[bool] = None,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        filter_: Dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        *,
        all_memories: Optional[bool] = None,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        filter_: Dict[str, Any] | None = None,
    ) -> List[ConversationMemory] | None:
        logger.info(
            f"{self.__class__.__name__} _arun: all_memories={all_memories}, query={query}"
        )
        store = self._get_store(store=self.store)
        # user_id is already in the namespace
        namespacer = NamespaceTemplate(self.namespace)
        namespace = namespacer()
        found_memories: List[SearchItem] = await store.asearch(
            namespace,
            query=query,
            filter=filter_,
            limit=limit,
            offset=offset,
        )
        return [ConversationMemory(**u.value) for u in found_memories]

    @staticmethod
    def _get_store(*, store: BaseStore | None = None) -> BaseStore:
        if store is not None:
            return store
        try:
            return get_store()
        except RuntimeError as e:
            raise errors.ConfigurationError("Could not get store") from e

    @staticmethod
    def _ensure_json_serializable(*, content: typing.Any) -> typing.Any:
        if isinstance(content, (str, int, float, bool, dict, list)):
            return content
        if hasattr(content, "model_dump"):
            try:
                return content.model_dump(mode="json")
            except Exception as e:
                logger.error(e)
                return str(content)
        return content
