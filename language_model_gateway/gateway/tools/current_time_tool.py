from datetime import datetime
from typing import Any, override

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


class CurrentTimeTool(ResilientBaseTool):
    name: str = "CurrentTime"
    description: str = "Useful for when you need to know the current time"

    @override
    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Returns the current time in Y-m-d H:M:S format with timezone."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S%Z%z")

    @override
    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(*args, **kwargs)
