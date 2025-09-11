import logging
import typing
from typing import Annotated, Literal, Type

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore
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
    action: Literal["create", "update", "delete"] = Field(
        description="Action to perform on the user profile"
    )
    state: Annotated[MyMessagesState, InjectedState] = Field()

    memory: ConversationMemory = Field(
        description="The memory data to create or update"
    )


class ManageMemoryTool(ResilientBaseTool):
    """
    Tool for managing persistent memories in conversations. Supports create, update, and delete actions.
    """

    name: str = "manage_memory"
    description: str = (
        "Create, update, or delete a memory to persist across conversations. "
        "Include the MEMORY ID when updating or deleting a MEMORY. Omit when creating a new MEMORY - it will be created for you. "
        "Proactively call this tool whenever there is a new message in the conversation, or when: "
        "1. You identify a new memory to save for later. "
        "2. You receive an explicit USER request to remember something or otherwise alter your behavior. "
        "3. You are working and want to record important context. "
        "4. You identify that an existing MEMORY is incorrect or outdated."
    )
    namespace: tuple[str, ...] | str
    args_schema: Type[BaseModel] = ConversationMemoryInput
    actions_permitted: typing.Optional[
        tuple[typing.Literal["create", "update", "delete"], ...]
    ] = ("create", "update", "delete")
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
        memory: ConversationMemory,
        action: str | None = None,
        state: Annotated[MyMessagesState, InjectedState],
    ) -> str:
        # use the user_id from the state since it is more reliable than the one the llm sets in the user_profile
        if not state.user_id:
            raise ToolException(
                "user_id is required in the state to store user profile"
            )
        memory.user_id = state.user_id
        store = self._get_store()
        if self.actions_permitted and action not in self.actions_permitted:
            raise ToolException(
                f"Invalid action {action}. Must be one of {self.actions_permitted}."
            )
        try:
            namespacer = NamespaceTemplate(self.namespace)
            namespace = namespacer()
            key: str = f"user_profile_{memory.user_id}"
            if action == "delete":
                await store.adelete(namespace, key=str(key))
                return f"Deleted user profile {key}"
            await store.aput(
                namespace,
                key=str(key),
                value=self._ensure_json_serializable(memory),
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
