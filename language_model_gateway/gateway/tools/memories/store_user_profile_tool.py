import logging
import typing
from typing import Type, Dict, Any, Annotated, Literal

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore
from langmem import errors
from pydantic import BaseModel, Field, ConfigDict

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.structures.user_profile import UserProfile
from language_model_gateway.gateway.tools.memories.user_profile_components import (
    UserProfileRepository,
    UserProfileValidator,
)
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class UserProfileInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
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
        "Update the existing user profile (or create a new one if it doesn't exist) based on the shared information.  Create one entry per user."
        "Proactively call this tool when you: "
        "1. Identify a new USER profile. "
        "2. Receive an explicit USER request to remember something or otherwise alter your behavior. "
        "3. Are working and want to record important memory. "
        "4. Identify that an existing USER profile is incorrect or outdated."
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
        logger.info(
            f"StoreUserProfileTool called with action: {action} state: {state} user_profile: {user_profile.model_dump()}"
        )
        try:
            # Validate state and action
            UserProfileValidator.validate_state_user_id(state)
            UserProfileValidator.validate_action(action, self.actions_permitted)
            # use the user_id from the state since it is more reliable than the one the llm sets in the user_profile
            if not state.user_id:
                raise ToolException(
                    "user_id is required in the state to store user profile"
                )
            user_profile.user_id = state.user_id
            store = self._get_store()
            repo = UserProfileRepository(store, self.namespace)
            if action == "delete":
                await repo.delete(user_profile.user_id)
                return f"Deleted user profile user_profile_{user_profile.user_id}"
            else:
                await repo.save(user_profile)
                return f"{action}d memory user_profile_{user_profile.user_id}"
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
