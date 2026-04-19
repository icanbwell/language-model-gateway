from __future__ import annotations

import logging
from typing import Type, override, TYPE_CHECKING

from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field, PrivateAttr

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

if TYPE_CHECKING:
    from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
        LanguageModelGatewayEnvironmentVariables,
    )

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class PythonReplToolInput(BaseModel):
    query: str = Field(description="A valid Python command to execute")


class PythonReplTool(ResilientBaseTool):
    name: str = "python_repl"
    description: str = "A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`."
    args_schema: Type[BaseModel] = PythonReplToolInput

    _environment_variables: LanguageModelGatewayEnvironmentVariables | None = (
        PrivateAttr(default=None)
    )

    def __init__(
        self,
        *,
        environment_variables: LanguageModelGatewayEnvironmentVariables | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._environment_variables = environment_variables

    def _should_log(self) -> bool:
        return bool(
            self._environment_variables
            and self._environment_variables.log_input_and_output
        )

    @override
    async def _arun(self, query: str) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        try:
            python_repl = PythonREPL()
            if self._should_log():
                logger.info(f"Running Python Repl with query: {query}")
            result: str = python_repl.run(command=query)
            if self._should_log():
                logger.info(f"Python Repl result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error running Python Repl: {e}")
            logger.exception(e, stack_info=True)
            return f"Error running Python Repl: {e}"

    @override
    def _run(self, query: str) -> str:
        try:
            python_repl = PythonREPL()
            if self._should_log():
                logger.info(f"Running Python Repl with query: {query}")
            result: str = python_repl.run(command=query)
            if self._should_log():
                logger.info(f"Python Repl result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error running Python Repl: {e}")
            logger.exception(e, stack_info=True)
            return f"Error running Python Repl: {e}"
