from typing import Any
from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


class CalculatorAverageInput(BaseModel):
    """
    Input model for CalculatorAverageTool

    Example input:
    {
        "numbers": [10, 20, 30]
    }
    """

    numbers: list[float] = Field(
        ...,
        description="List of numbers to calculate the average. Example: [10, 20, 30]"
    )


class CalculatorAverageTool(ResilientBaseTool):
    """
    LangChain-compatible tool for calculating the average of a list of numbers.

    Example usage:
    - Input: [10, 20, 30]
    - Output: "The average of the provided numbers is: 20.0"
    """

    name: str = "CalculatorAverageTool"
    description: str = "Useful for when you need to calculate the average of a list of numbers"
    args_schema: type[BaseModel] = CalculatorAverageInput


    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Run the tool to calculate the average of a list of numbers"""
        input_data = self.args_schema(**kwargs)
        numbers = input_data.numbers

        if not numbers:
            return "No numbers provided to calculate the average."

        average = float(sum(numbers)) / len(numbers) if len(numbers) > 0 else 0.0
        return f"The average of the provided numbers is: {average}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(*args, **kwargs)
