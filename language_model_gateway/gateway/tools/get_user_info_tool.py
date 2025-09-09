from typing import Annotated

from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


class GetUserInfoTool(ResilientBaseTool):
    name: str = "get_user_profile"
    description: str = "Look up user profile for a given user."

    def _run(self, state: Annotated[MyMessagesState, InjectedState]) -> str:
        user_id = state.user_id
        if not user_id:
            raise ValueError("user_id is required")

        my_store: BaseStore = get_store()
        user_info = my_store.get(("memories",), user_id)

        # user_info2 = my_store.search(("memories", user_id, "user_profile"))
        return str(user_info.value) if user_info else "Unknown user"
