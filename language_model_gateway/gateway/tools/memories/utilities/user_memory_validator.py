import logging
from typing import Any, Optional

from langchain_core.tools import ToolException


logger = logging.getLogger(__name__)


class UserMemoryValidator:
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
            raise ToolException("user_id is required in the state to store user memory")
        if not getattr(state, "conversation_id", None):
            raise ToolException(
                "conversation_id is required in the state to store user memory"
            )
