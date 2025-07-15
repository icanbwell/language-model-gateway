import asyncio
from typing import List
import logging

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class CalculatorAverageTool(ResilientBaseTool):
    """
    LangChain-compatible tool for calculating the average of a list of numbers.

    Example usage:
    - Input: [10, 20, 30]
    - Output: "The average of the provided numbers is: 20.0"
    """

    logger.info("Initializing CalculatorAverageTool")

    name: str = "CalculatorAverageTool"
    description: str = (
        "Useful for when you need to calculate the average of a list of numbers"
    )

    async def _arun(self, numbers: List[float]) -> str:
        """Run the tool to calculate the average of a list of numbers"""
        logger.info(f"CalculatorAverageTool _arun called with numbers: {numbers}")

        if not numbers:
            logger.warning("No numbers provided to calculate the average.")
            return "No numbers provided to calculate the average."

        try:
            # Ensure all inputs are convertible to float
            numbers = [float(num) for num in numbers]
            average = sum(numbers) / len(numbers)
            logger.info(f"Calculated average: {average}")
            return f"The average of the provided numbers is: {average}"
        except (TypeError, ValueError) as e:
            logger.error(f"Error converting numbers: {e}")
            return f"Error: Could not convert all inputs to numbers. {e}"

    def _run(self, numbers: List[float]) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return asyncio.run(self._arun(numbers=numbers))
