from typing import override, Any, Optional

from langchain_core.callbacks import AsyncCallbackManagerForToolRun
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool


class StructuredToolWithOutputLimits(StructuredTool):
    @override
    async def _arun(
        self,
        *args: Any,
        config: RunnableConfig,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        return super()._arun(
            args=args,
            config=config,
            run_manager=run_manager,
            kwargs=kwargs,
        )
