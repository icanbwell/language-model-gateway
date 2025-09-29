import logging
from typing import Any, Optional

from langchain_core.tools import ToolException
from langgraph.store.base import BaseStore
from langmem.utils import NamespaceTemplate

from language_model_gateway.gateway.structures.user_profile import UserProfile

logger = logging.getLogger(__name__)


class UserProfileRepository:
    def __init__(self, store: BaseStore, namespace: str | tuple[str, ...]):
        self.store = store
        self.namespace = NamespaceTemplate(namespace)()

    async def save(self, user_profile: UserProfile) -> None:
        user_profile_id = f"user_profile_{user_profile.user_id}"
        await self.store.aput(
            self.namespace,
            key=user_profile_id,
            value=UserProfileSerializer.serialize(user_profile),
        )

    async def delete(self, user_id: str) -> None:
        user_profile_id = f"user_profile_{user_id}"
        await self.store.adelete(self.namespace, key=user_profile_id)


class UserProfileValidator:
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
            raise ToolException(
                "user_id is required in the state to store user profile"
            )


class UserProfileSerializer:
    @staticmethod
    def serialize(content: Any) -> Any:
        if isinstance(content, (str, int, float, bool, dict, list)):
            return content
        if hasattr(content, "model_dump"):
            try:
                return content.model_dump(mode="json")
            except Exception as e:
                logger.error(e)
                return str(content)
        return content
