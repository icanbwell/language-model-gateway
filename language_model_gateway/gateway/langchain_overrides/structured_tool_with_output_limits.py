import logging
from typing import override, Any, Optional

from langchain_core.callbacks import AsyncCallbackManagerForToolRun
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from language_model_gateway.gateway.utilities.token_counter.token_counter import (
    TokenReducer,
)

logger = logging.getLogger(__name__)


class StructuredToolWithOutputLimits(StructuredTool):
    limit_output_tokens: Optional[int] = None
    """The maximum number of tokens to return in the output. If None, no limit is applied."""

    token_reducer: TokenReducer
    """The TokenReducer instance used to count and reduce tokens."""

    @override
    async def _arun(
        self,
        *args: Any,
        config: RunnableConfig,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        # log input params and output
        logger.info(
            f"StructuredToolWithOutputLimits input args: {args}, kwargs: {kwargs}"
        )
        result = await super()._arun(
            *args,
            config=config,
            run_manager=run_manager,
            **kwargs,
        )
        logger.info(
            f"StructuredToolWithOutputLimits output before token limit: {type(result)}\n{result}"
        )
        if self.limit_output_tokens is not None:
            if isinstance(result, str):
                token_count = self.token_reducer.count_tokens(result)
                if token_count > self.limit_output_tokens:
                    result = self.token_reducer.reduce_tokens(
                        text=result,
                        max_tokens=self.limit_output_tokens,
                        preserve_start=0,
                    )
            elif isinstance(result, tuple):
                # find the largest string in the tuple and apply truncation to that
                str_indices = [i for i, v in enumerate(result) if isinstance(v, str)]
                if str_indices:
                    largest_str_index = max(
                        str_indices,
                        key=lambda i: self.token_reducer.count_tokens(result[i]),
                    )
                    token_count = self.token_reducer.count_tokens(
                        result[largest_str_index]
                    )
                    if token_count > self.limit_output_tokens:
                        reduced_str = self.token_reducer.reduce_tokens(
                            text=result[largest_str_index],
                            max_tokens=self.limit_output_tokens,
                            preserve_start=0,
                        )
                        result = (
                            result[:largest_str_index]
                            + (reduced_str,)
                            + result[largest_str_index + 1 :]
                        )

        logger.info(
            f"StructuredToolWithOutputLimits output after token limit: {type(result)}\n{result}"
        )
        return result
