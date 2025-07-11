import asyncio

import math
from typing import Any
from pydantic import BaseModel, Field
import logging

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


logger = logging.getLogger(__name__)


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

    async def _arun(self, numbers: list[float]) -> str:
        """Run the tool to calculate the standard deviation of a list of numbers"""
        logger.info("Starting standard deviation calculation.")
        logger.debug(f"Input numbers: {numbers}")

        if not numbers:
            logger.warning("No numbers provided to calculate the standard deviation.")
            return "No numbers provided to calculate the standard deviation."

        if len(numbers) == 1:
            logger.info("Only one number provided. Standard deviation is 0.0.")
            return "Standard deviation of a single number is: 0.0"

        # Calculate mean
        mean = sum(numbers) / len(numbers)
        logger.debug(f"Calculated mean: {mean}")

        # Calculate variance (average of squared differences from mean)
        variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
        logger.debug(f"Calculated variance: {variance}")

        # Standard deviation is square root of variance
        stddev = math.sqrt(variance)
        logger.info(f"Calculated standard deviation: {stddev:.2f}")

        return f"The standard deviation of the provided numbers is: {stddev:.2f}"

    def _run(self, numbers: list[float]) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return asyncio.run(self._arun(numbers=numbers))