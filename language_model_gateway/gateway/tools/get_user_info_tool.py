import logging
from typing import Annotated, List, Any, Dict

from langchain_core.tools import ToolException
from langgraph.config import get_store
from langgraph.prebuilt import InjectedState
from langgraph.store.base import BaseStore, SearchItem

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.structures.user_profile import UserProfile
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class GetUserInfoTool(ResilientBaseTool):
    name: str = "get_user_profile"
    description: str = "Look up user profile for a given user."

    def _run(self, state: Annotated[MyMessagesState, InjectedState]) -> str:
        logger.info(f"GetUserInfoTool called with state: {state}")

        try:
            user_id = state.user_id
            if not user_id:
                raise ValueError("user_id is required")

            my_store: BaseStore = get_store()
            # user_info = my_store.get(("memories",), user_id)

            user_info_items: List[SearchItem] = my_store.search(
                ("memories", user_id, "user_profile")
            )
            if not user_info_items:
                return "Unknown user"
            user_info_value: Dict[str, Any] = user_info_items[0].value
            user_profile: UserProfile = UserProfile.model_validate(user_info_value)
            logger.info(
                f"GetUserInfoTool: user_info_value: {user_info_value}, text={user_profile.to_text()}"
            )
            return user_profile.to_text()
        except Exception as e:
            logger.exception(e)
            raise ToolException(str(e))
