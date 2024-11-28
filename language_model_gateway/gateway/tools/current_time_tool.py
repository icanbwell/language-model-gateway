from datetime import datetime
from typing import Any

from langchain_core.tools import BaseTool


class CurrentTimeTool(BaseTool):
    name: str = "CurrentTime"
    description: str = "Useful for when you need to know the current time"

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Returns the current time in Y-m-d H:M:S format with timezone."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S%Z%z")

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(*args, **kwargs)
