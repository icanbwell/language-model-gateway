from typing import Any
from pydantic import BaseModel, Field
import logging

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__file__)


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
        description="List of numbers to calculate the average. Example: [10.0, 20, 30]"
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

    def _run(self, numbers: list[float]) -> str:
        """Run the tool to calculate the average of a list of numbers"""
        logger.info("CalculatorAverageTool_run called with numbers: %s", numbers)
        logger.debug("Numbers received for averaging: %s", numbers)

        if not numbers:
            logger.warning("No numbers provided to calculate the average.")
            return "No numbers provided to calculate the average."

        try:
            # Ensure all inputs are convertible to float
            numbers = [float(num) for num in numbers]
            average = sum(numbers) / len(numbers)
            logger.info("Calculated average: %f", average)
            return f"The average of the provided numbers is: {average}"
        except (TypeError, ValueError) as e:
            logger.error(f"Error converting numbers: {e}")
            return f"Error: Could not convert all inputs to numbers. {e}"

    async def _arun(self, numbers: list[float]) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return self._run(numbers)