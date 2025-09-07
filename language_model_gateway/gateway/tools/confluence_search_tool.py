import logging
from typing import Type, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.confluence.confluence_helper import (
    ConfluenceHelper,
)
from language_model_gateway.gateway.utilities.csv_to_markdown_converter import (
    CsvToMarkdownConverter,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class ConfluenceSearchToolInput(BaseModel):
    """
    Input model for configuring Confluence search and analysis.

    """

    search_string: str = Field(
        ..., description="The search string to use for querying Confluence content."
    )
    limit: Optional[int] = Field(
        default=10, description="Maximum number of search results to retrieve."
    )


class ConfluenceSearchTool(ResilientBaseTool):
    name: str = "confluence_search_tool"
    description: str = (
        "Tool for searching content in Confluence. "
        "USAGE TIPS: "
        "- Provide a search string to search content in Confluence."
        "- Indicate the Confluence space to limit the search results."
    )

    args_schema: Type[BaseModel] = ConfluenceSearchToolInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    confluence_helper: ConfluenceHelper

    async def _arun(self, search_string: str, limit: int = 10) -> Tuple[str, str]:
        try:
            search_results = await self.confluence_helper.search_content(
                search_string, limit
            )

            logger.info(f"CONFLUENCE SEARCH TOOL, RESULTS:\n{search_results}")

            if not search_results:
                return "No results found.", "No results found."

            csv_results = self.confluence_helper.format_results_as_csv(search_results)
            csv_results_display = (
                self.confluence_helper.format_results_as_csv_for_display(search_results)
            )
            markdown_results = CsvToMarkdownConverter.csv_to_markdown_table(
                csv_results_display
            )

            artifact = f"Search results for query: {search_string}\n\nResults:\n{markdown_results}"
            return csv_results, artifact
        except Exception as e:
            error_msg = f"Error searching Confluence content: {str(e)}"
            return error_msg, error_msg

    def _run(self, search_string: str, limit: Optional[int] = 10) -> Tuple[str, str]:
        """
        Synchronous version of the tool (falls back to async implementation).

        Raises:
            NotImplementedError: Always raises to enforce async usage
        """
        raise NotImplementedError("Use async version of this tool")
