import math
from typing import Any
from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


class CalculatorStddevInput(BaseModel):
    """
    Input model for CalculatorStddevTool

    Example input:
    {
        "numbers": [10, 20, 30]
    }
    """

    numbers: list[float] = Field(
        ...,
        description="List of numbers to calculate the standard deviation. Example: [10, 20, 30]"
    )


class CalculatorStddevTool(ResilientBaseTool):
    """
    LangChain-compatible tool for calculating the standard deviation of a list of numbers.

    Example usage:
    - Input: [10, 20, 30]
    - Output: "The standard deviation of the provided numbers is: 8.16"
    """

    name: str = "CalculatorStddevTool"
    description: str = "Useful for when you need to calculate the standard deviation of a list of numbers"
    args_schema: type[BaseModel] = CalculatorStddevInput

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Run the tool to calculate the standard deviation of a list of numbers"""
        input_data = self.args_schema(**kwargs)
        numbers = input_data.numbers

        if not numbers:
            return "No numbers provided to calculate the standard deviation."

        if len(numbers) == 1:
            return "Standard deviation of a single number is: 0.0"

        # Calculate mean
        mean = sum(numbers) / len(numbers)

        # Calculate variance (average of squared differences from mean)
        variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)

        # Standard deviation is square root of variance
        stddev = math.sqrt(variance)

        return f"The standard deviation of the provided numbers is: {stddev:.2f}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(*args, **kwargs)