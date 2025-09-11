import logging
import typing
from typing import Type, Dict, Any, Annotated, Literal

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore
from langmem import errors
from langmem.utils import NamespaceTemplate
from pydantic import BaseModel, Field

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.structures.user_profile import UserProfile
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class UserProfileInput(BaseModel):
    action: Literal["create", "update", "delete"] = Field(
        description="Action to perform on the user profile"
    )
    state: Annotated[MyMessagesState, InjectedState] = Field()

    user_profile: UserProfile = Field(
        description="The user profile data to create or update"
    )


class StoreUserProfileTool(ResilientBaseTool):
    """
    Tool for managing persistent memories in conversations. Supports create, update, and delete actions.
    """

    name: str = "store_user_profile"
    description: str = (
        "Create, update, or delete a user profile to persist across conversations. "
        "Proactively call this tool when you: "
        "1. Identify a new USER profile. "
        "2. Receive an explicit USER request to remember something or otherwise alter your behavior. "
        "3. Are working and want to record important context. "
        "4. Identify that an existing MEMORY is incorrect or outdated."
    )
    args_schema: Type[BaseModel] = UserProfileInput
    namespace: tuple[str, ...] | str
    actions_permitted: typing.Optional[
        tuple[typing.Literal["create", "update", "delete"], ...]
    ] = ("create", "update", "delete")
    store: typing.Optional[BaseStore] = None

    def _run(
        self,
        name: str,
        age: int | None,
        recent_memories: list[str],
        preferences: Dict[str, Any] | None,
        action: str,
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        *,
        user_profile: UserProfile,
        action: str | None = None,
        state: Annotated[MyMessagesState, InjectedState],
    ) -> str:
        # use the user_id from the state since it is more reliable than the one the llm sets in the user_profile
        if not state.user_id:
            raise ToolException(
                "user_id is required in the state to store user profile"
            )
        user_profile.user_id = state.user_id
        store = self._get_store()
        if self.actions_permitted and action not in self.actions_permitted:
            raise ToolException(
                f"Invalid action {action}. Must be one of {self.actions_permitted}."
            )
        try:
            namespacer = NamespaceTemplate(self.namespace)
            namespace = namespacer()
            user_profile_id: str = f"user_profile_{user_profile.user_id}"
            if action == "delete":
                await store.adelete(namespace, key=str(user_profile_id))
                return f"Deleted user profile {user_profile_id}"
            await store.aput(
                namespace,
                key=str(user_profile_id),
                value=self._ensure_json_serializable(user_profile),
            )
            return f"{action}d memory {user_profile_id}"
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
