import asyncio
from typing import Any
from pydantic import BaseModel, Field
import logging

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


logger = logging.getLogger(__name__)


class CalculatorLengthInput(BaseModel):
    """
    Input model for CalculatorLengthTool

    Example input:
    {
        "items": ["apple", "banana", "cherry"]
    }
    """

    items: list[Any] = Field(
        ...,
        description="List of items to calculate the length. Can contain any type of items. Example: ['apple', 'banana', 'cherry']"
    )


class CalculatorLengthTool(ResilientBaseTool):
    """
    LangChain-compatible tool for calculating the length (count) of a list of items.

    Example usage:
    - Input: ["apple", "banana", "cherry"]
    - Output: "The length of the provided list is: 3"
    """

    name: str = "CalculatorLengthTool"
    description: str = "Useful for when you need to calculate the length (count) of a list of items"
    args_schema: type[BaseModel] = CalculatorLengthInput

    async def _arun(self, items: list[Any]) -> str:
        """Run the tool to calculate the length of a list of items"""
        logger.info("CalculatorLengthTool _run called with args: %s, kwargs: %s", args, kwargs)

        if items is None:
            logger.warning("No list provided to calculate the length.")
            return "No list provided to calculate the length."

        length = len(items)
        logger.info("Calculated length: %d for items: %s", length, items)
        return f"The length of the provided list is: {length}"

    def _run(self, items: list[Any]) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return asyncio.run(self._arun(items=items))