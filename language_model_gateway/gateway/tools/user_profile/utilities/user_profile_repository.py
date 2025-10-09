import logging

from langgraph.store.base import BaseStore
from langmem.utils import NamespaceTemplate

from language_model_gateway.gateway.tools.user_profile.structures.user_profile import (
    UserProfile,
)
from language_model_gateway.gateway.tools.user_profile.utilities.user_profile_serializer import (
    UserProfileSerializer,
)

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
