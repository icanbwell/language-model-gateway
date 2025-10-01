import logging
import typing
from typing import Type, Annotated, Literal

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore
from langmem import errors
from pydantic import BaseModel, Field, ConfigDict

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.structures.conversation_memory import (
    ConversationMemory,
)
from language_model_gateway.gateway.tools.memories.user_memory_components import (
    UserMemoryRepository,
    UserMemoryValidator,
)
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class UserMemoryInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
    action: Literal["create", "update", "delete"] = Field(
        description="Action to perform on the user memory"
    )
    state: Annotated[MyMessagesState, InjectedState] = Field()
    user_memory: ConversationMemory = Field(
        description="The user memory data to create or update"
    )


class StoreUserMemoryTool(ResilientBaseTool):
    """
    Tool for managing persistent user memories in conversations. Supports create, update, and delete actions.
    """

    name: str = "store_user_memory"
    description: str = (
        "Update the existing user memory (or create a new one if it doesn't exist) based on the shared information. Create one entry per user per conversation. "
        "Proactively call this tool when you: "
        "1. Identify a new USER memory. "
        "2. Receive an explicit USER request to remember something or otherwise alter your behavior. "
        "3. Are working and want to record important memory. "
        "4. Identify that an existing USER memory is incorrect or outdated."
    )
    args_schema: Type[BaseModel] = UserMemoryInput
    namespace: tuple[str, ...] | str
    actions_permitted: typing.Optional[
        tuple[typing.Literal["create", "update", "delete"], ...]
    ] = ("create", "update", "delete")
    store: typing.Optional[BaseStore] = None

    def _run(
        self,
        user_id: str,
        conversation_id: str,
        name: str,
        recent_memories: list[str],
        action: str,
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        *,
        user_memory: ConversationMemory,
        action: str | None = None,
        state: Annotated[MyMessagesState, InjectedState],
    ) -> str:
        logger.info(
            f"StoreUserMemoryTool called with action: {action} state: {state} user_memory: {user_memory.model_dump()}"
        )
        try:
            # Validate state and action
            UserMemoryValidator.validate_state_user_id(state)
            UserMemoryValidator.validate_action(action, self.actions_permitted)
            # use the user_id and conversation_id from the state since they are more reliable
            if not state.user_id or not state.conversation_thread_id:
                raise ToolException(
                    "user_id and conversation_id are required in the state to store user memory"
                )
            user_memory.user_id = state.user_id
            user_memory.conversation_id = state.conversation_thread_id
            store = self._get_store()
            repo = UserMemoryRepository(store, self.namespace)
            if action == "delete":
                await repo.delete(user_memory.user_id, user_memory.conversation_id)
                return f"Deleted user memory user_memory_{user_memory.user_id}_{user_memory.conversation_id}"
            else:
                await repo.save(user_memory)
                return f"{action}d memory user_memory_{user_memory.user_id}_{user_memory.conversation_id}"
        except Exception as e:
            logger.exception("Error storing user memory")
            raise ToolException("Error storing user memory") from e

    def _get_store(self) -> BaseStore:
        if self.store is not None:
            return self.store
        try:
            return get_store()
        except RuntimeError as e:
            raise errors.ConfigurationError("Could not get store") from e
