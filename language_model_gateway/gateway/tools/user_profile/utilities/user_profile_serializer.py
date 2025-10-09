import logging
from typing import Any

logger = logging.getLogger(__name__)


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
