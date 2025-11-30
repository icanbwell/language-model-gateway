from pydantic import BaseModel, Field
from typing import Type, Optional, Tuple, Literal, Any, override
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.databricks.databricks_helper import (
    DatabricksHelper,
)


class DatabricksSQLInput(BaseModel):
    """
    Enhanced input model for Databricks with API validation
    """

    fhir_request: Optional[str] = Field(
        default=None,
        description=("Request to be created into a query. "),
    )


class DatabricksSQLTool(ResilientBaseTool):
    """
    Enhanced Databricks Agent Tool with API Validation
    """

    name: str = "databricks_tool"
    description: str = (
        "A tool for querying FHIR data from Databricks. "
        "USAGE TIPS: "
        "- If you believe a query will return a large amount of data, please use the 'limit' keyword in the query. For example: 'Get all patients with diabetes diagnosis' would return a lot of results. If you are limiting, tell the user beforehand. "
        "- Check the query before running it. Make sure if calling nested fields that you have accounted for proper explosion of those fields into new tables. Join accordingly. "
        "- Take the natural language query, convert it into SQL, and present that SQL in clear SQL format to the user prior to sending to Databricks. "
        "Example queries: "
        "'Get all patients with diabetes diagnosis'. "
        "'Get demographics of patients'. "
        "'Get all patients with diabetes and a count of their encounters'. "
    )
    args_schema: Type[DatabricksSQLInput] = DatabricksSQLInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    databricks_helper: DatabricksHelper

    @override
    def _run(
        self,
        fhir_request: Optional[str] = None,
    ) -> Tuple[str, Any]:
        raise NotImplementedError("Use async version of this tool")

    @override
    async def _arun(self, fhir_request: str) -> Tuple[str, str]:
        if not fhir_request or not fhir_request.strip():
            raise ValueError("Query cannot be empty or None")
        results = self.databricks_helper.execute_query(fhir_request)
        artifact = f"\n\nDatabricksSQLTool: Query Results\n {results}"

        return results, artifact
