from typing import Any
from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


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

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Run the tool to calculate the length of a list of items"""
        input_data = self.args_schema(**kwargs)
        items = input_data.items

        if items is None:
            return "No list provided to calculate the length."

        length = len(items)
        return f"The length of the provided list is: {length}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(*args, **kwargs)