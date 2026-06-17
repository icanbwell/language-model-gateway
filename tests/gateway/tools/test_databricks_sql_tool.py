import pytest
from unittest.mock import Mock

from language_model_gateway.gateway.tools.databricks_sql_tool import DatabricksSQLTool
from language_model_gateway.gateway.tools.databricks_sql_tool import DatabricksSQLInput
from language_model_gateway.gateway.utilities.databricks.databricks_helper import (
    DatabricksHelper,
)


@pytest.fixture
def mock_databricks_helper() -> Mock:
    """Fixture to create a mock DatabricksHelper"""
    return Mock(spec=DatabricksHelper)


@pytest.fixture
def databricks_sql_tool(mock_databricks_helper: Mock) -> DatabricksSQLTool:
    """Fixture to create a DatabricksSQLTool instance"""
    return DatabricksSQLTool(databricks_helper=mock_databricks_helper)


@pytest.mark.asyncio
async def test_databricks_sql_tool_successful_query(
    databricks_sql_tool: DatabricksSQLTool, mock_databricks_helper: Mock
) -> None:
    """
    Test successful query execution
    """
    # Arrange
    test_query = "SELECT * FROM patients LIMIT 10"
    mock_result = "| id | name |\n| --- | --- |\n| 1 | John Doe |"
    mock_databricks_helper.execute_query.return_value = mock_result

    # Act
    result, artifact = await databricks_sql_tool._arun(fhir_request=test_query)

    # Assert
    assert result == mock_result
    assert "DatabricksSQLTool: Query Results" in artifact
    mock_databricks_helper.execute_query.assert_called_once_with(query=test_query)


@pytest.mark.asyncio
async def test_databricks_sql_tool_empty_query(
    databricks_sql_tool: DatabricksSQLTool, mock_databricks_helper: Mock
) -> None:
    """
    Test query with empty input
    """
    # Arrange
    test_query = ""

    # Act & Assert
    with pytest.raises(ValueError):
        await databricks_sql_tool._arun(fhir_request=test_query)


@pytest.mark.asyncio
async def test_databricks_sql_tool_error_handling(
    databricks_sql_tool: DatabricksSQLTool, mock_databricks_helper: Mock
) -> None:
    """
    Test error handling during query execution
    """
    # Arrange
    test_query = "SELECT * FROM non_existent_table"
    mock_error_result = "Error executing Databricks query: Table not found"
    mock_databricks_helper.execute_query.return_value = mock_error_result

    # Act
    result, artifact = await databricks_sql_tool._arun(fhir_request=test_query)

    # Assert
    assert result == mock_error_result
    assert "DatabricksSQLTool: Query Results" in artifact
    mock_databricks_helper.execute_query.assert_called_once_with(query=test_query)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM patients LIMIT 10",
        "GET demographics of patients",
        "Find all patients with diabetes diagnosis",
    ],
)
@pytest.mark.asyncio
async def test_databricks_sql_tool_multiple_queries(
    databricks_sql_tool: DatabricksSQLTool, mock_databricks_helper: Mock, query: str
) -> None:
    """
    Parameterized test for multiple query types
    """
    # Arrange
    mock_result = f"| Result for query: {query} |"
    mock_databricks_helper.execute_query.return_value = mock_result

    # Act
    result, artifact = await databricks_sql_tool._arun(fhir_request=query)

    # Assert
    assert result == mock_result
    assert "DatabricksSQLTool: Query Results" in artifact
    mock_databricks_helper.execute_query.assert_called_once_with(query=query)


def test_databricks_sql_tool_response_format(
    databricks_sql_tool: DatabricksSQLTool,
) -> None:
    """
    Test the response format of the tool
    """
    # Assert
    assert databricks_sql_tool.response_format == "content_and_artifact"


def test_databricks_sql_tool_description() -> None:
    """
    Test the tool's description
    """
    tool = DatabricksSQLTool(databricks_helper=Mock(spec=DatabricksHelper))

    # Assert
    assert "A tool for querying FHIR data from Databricks" in tool.description
    assert "USAGE TIPS" in tool.description
    assert "limit" in tool.description
    assert "Example queries" in tool.description


def test_databricks_sql_input_model() -> None:
    """
    Test the DatabricksSQLInput Pydantic model
    """
    # Test with valid input
    valid_input = DatabricksSQLInput(fhir_request="SELECT * FROM patients")
    assert valid_input.fhir_request == "SELECT * FROM patients"

    # Test with None input
    none_input = DatabricksSQLInput()
    assert none_input.fhir_request is None


def test_databricks_sql_tool_name() -> None:
    """
    Test the tool's name
    """
    tool = DatabricksSQLTool(databricks_helper=Mock(spec=DatabricksHelper))

    # Assert
    assert tool.name == "databricks_tool"


@pytest.mark.asyncio
async def test_databricks_sql_tool_sync_run_not_implemented(
    databricks_sql_tool: DatabricksSQLTool,
) -> None:
    """
    Test that the synchronous _run method raises NotImplementedError
    """
    # Act & Assert
    with pytest.raises(NotImplementedError, match="Use async version of this tool"):
        databricks_sql_tool._run(fhir_request="test query")


@pytest.mark.parametrize("input_query", [None, "", "   "])
@pytest.mark.asyncio
async def test_databricks_sql_tool_empty_or_none_input(
    databricks_sql_tool: DatabricksSQLTool, input_query: str
) -> None:
    """
    Test handling of empty or None input
    """
    # Act & Assert
    with pytest.raises(ValueError, match="Query cannot be empty or None"):
        await databricks_sql_tool._arun(fhir_request=input_query)
