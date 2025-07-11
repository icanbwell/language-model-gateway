import pytest
from language_model_gateway.gateway.tools.calculator_average_tool import CalculatorAverageTool


async def test_calculator_average_tool_basic() -> None:
    """Test basic average calculation"""
    tool = CalculatorAverageTool()
    result = await tool._arun(numbers=[10, 20, 30])
    print(result)
    assert "The average of the provided numbers is: 20.0" in result


async def test_calculator_average_tool_single_number() -> None:
    """Test average calculation with single number"""
    tool = CalculatorAverageTool()
    result = await tool._arun(numbers=[42])
    print(result)
    assert "The average of the provided numbers is: 42.0" in result


async def test_calculator_average_tool_empty_list() -> None:
    """Test average calculation with empty list"""
    tool = CalculatorAverageTool()
    result = await tool._arun(numbers=[])
    print(result)
    assert "No numbers provided to calculate the average." in result


async def test_calculator_average_tool_floats() -> None:
    """Test average calculation with floating point numbers"""
    tool = CalculatorAverageTool()
    result = await tool._arun(numbers=[1.5, 2.5, 3.0])
    print(result)
    assert "The average of the provided numbers is: 2.333333333333333" in result


async def test_calculator_average_tool_negative_numbers() -> None:
    """Test average calculation with negative numbers"""
    tool = CalculatorAverageTool()
    result = await tool._arun(numbers=[-10, 0, 10])
    print(result)
    assert "The average of the provided numbers is: 0.0" in result