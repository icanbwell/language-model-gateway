import asyncio
from typing import List
import logging

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool


logger = logging.getLogger(__name__)


class CalculatorSumTool(ResilientBaseTool):
    """
    LangChain-compatible tool for calculating the sum of a list of numbers.

    Example usage:
    - Input: [10, 20, 30]
    - Output: "The sum of the provided numbers is: 60.0"
    """

    name: str = "CalculatorSumTool"
    description: str = (
        "Useful for when you need to calculate the sum of a list of numbers"
    )

    async def _arun(self, numbers: List[float]) -> str:
        """Run the tool to calculate the sum of a list of numbers"""
        logger.debug(f"Received numbers for sum: {numbers}")

        if not numbers:
            logger.warning("No numbers provided to calculate the sum.")
            return "No numbers provided to calculate the sum."

        total = sum(numbers)
        logger.info(f"Calculated sum: {total}")
        return f"The sum of the provided numbers is: {total}"

    def _run(self, numbers: List[float]) -> str:
        """Async implementation of the tool (in this case, just calls _run)"""
        return asyncio.run(self._arun(numbers=numbers))
