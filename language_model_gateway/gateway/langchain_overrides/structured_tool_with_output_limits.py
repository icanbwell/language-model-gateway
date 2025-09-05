import json
import logging
from typing import override, Any, Optional, Dict, List

from langchain_core.callbacks import AsyncCallbackManagerForToolRun
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)

logger = logging.getLogger(__name__)


class StructuredToolWithOutputLimits(StructuredTool):
    """
    A StructuredTool that limits the output based on token count using a TokenReducer.
    Inherits from langchain's StructuredTool and adds functionality to limit the output
    based on the number of tokens.
    """

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
                    logger.info(
                        f"StructuredToolWithOutputLimits output after truncation: {type(result)}\n{result}"
                    )

            elif isinstance(result, tuple):
                result_dict_str: str
                result_dict_str, _ = result
                result_dict: Dict[str, Any] | List[Dict[str, Any]] = json.loads(
                    result_dict_str
                )
                # find the largest string in the dict or list of dicts and apply truncation to it
                if isinstance(result_dict, dict):
                    largest_str_key = max(
                        result_dict,
                        key=lambda k: len(result_dict[k])
                        if isinstance(result_dict[k], str)
                        else 0,
                    )
                    if isinstance(result_dict[largest_str_key], str):
                        token_count = self.token_reducer.count_tokens(
                            result_dict[largest_str_key]
                        )
                        if token_count > self.limit_output_tokens:
                            result_dict[largest_str_key] = (
                                self.token_reducer.reduce_tokens(
                                    text=result_dict[largest_str_key],
                                    max_tokens=self.limit_output_tokens,
                                    preserve_start=0,
                                )
                            )
                            result = (json.dumps(result_dict), None)
                            logger.info(
                                f"StructuredToolWithOutputLimits output after truncation: {type(result)}\n{result}"
                            )

                elif isinstance(result_dict, list):
                    for item in result_dict:
                        if isinstance(item, dict):
                            largest_str_key = max(
                                item,
                                key=lambda k: len(item[k])
                                if isinstance(item[k], str)
                                else 0,
                            )
                            if isinstance(item[largest_str_key], str):
                                token_count = self.token_reducer.count_tokens(
                                    item[largest_str_key]
                                )
                                if token_count > self.limit_output_tokens:
                                    item[largest_str_key] = (
                                        self.token_reducer.reduce_tokens(
                                            text=item[largest_str_key],
                                            max_tokens=self.limit_output_tokens,
                                            preserve_start=0,
                                        )
                                    )
                    result = (json.dumps(result_dict), None)
                    logger.info(
                        f"StructuredToolWithOutputLimits output after truncation: {type(result)}\n{result}"
                    )

            else:
                logger.warning(
                    f"StructuredToolWithOutputLimits received unsupported result type for token limiting: {type(result)}"
                )

        return result
