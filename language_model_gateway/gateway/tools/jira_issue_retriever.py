import logging
from typing import Type, Tuple, Literal, override
from pydantic import BaseModel, Field
from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.jira.jira_issue_result import (
    JiraIssueResult,
)
from language_model_gateway.gateway.utilities.jira.jira_issues_helper import (
    JiraIssueHelper,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class JiraIssueRetrieverAgentInput(BaseModel):
    """
    Input model for retrieving a specific Jira issue by ID.
    """

    issue_id: str = Field(
        default="",
        description="The ID of the Jira issue to retrieve. It typically follows this format: 2-4 capital letters + hyphen or space + 1-5 digits. Examples: ATC-1234, Atc 6789, EFS-564",
    )


class JiraIssueRetriever(ResilientBaseTool):
    """
    A LangChain-compatible tool for retrieving a specific Jira issue by ID.
    """

    name: str = "jira_issue_retriever"
    description: str = (
        "Tool to retrieve a specific Jira issue by ID. "
        "USAGE TIPS: "
        "- Provide the Jira issue ID to retrieve the issue details."
        "- ID typically follows this format: 2-4 capital letters + hyphen or space + 1-5 digits. Examples: ATC-1234, Atc 6789, EFS-564"
    )

    args_schema: Type[BaseModel] = JiraIssueRetrieverAgentInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    jira_issues_helper: JiraIssueHelper

    @override
    async def _arun(
        self,
        issue_id: str,
    ) -> Tuple[str, str]:
        """
        Asynchronous version of the Jira Issue by ID tool.

        Returns:
            Tuple of Jira issue text and artifact description
        """
        log_prefix: str = f"JiraIssueRetriever: issue_id={issue_id}"

        try:
            jira_issue_result: JiraIssueResult = (
                await self.jira_issues_helper.retrieve_issue_by_id(issue_id=issue_id)
            )

            if jira_issue_result.error:
                error_msg = f"Error retrieving Jira issue: {jira_issue_result.error}"
                error_artifact = (
                    log_prefix + f" Retrieval Failed: {jira_issue_result.error}"
                )
                logger.error(error_msg)
                return error_msg, error_artifact

            jira_issue = jira_issue_result.issues[0]

            full_text = (
                f"**Id**: {jira_issue.key}\n"
                f"**Summary**: {jira_issue.summary}\n"
                f"**Status**: {jira_issue.status}\n"
                f"**Assignee**: {jira_issue.assignee}\n"
                f"**Created**: {jira_issue.created_at}\n"
                f"**Closed**: {jira_issue.closed_at}\n"
                f"**Description**: {jira_issue.description}\n"
            )

            artifact = log_prefix + f", Retrieved issue {jira_issue.key}.\n\n"
            artifact += f"\n{full_text}"

            return full_text, artifact

        except Exception as e:
            error_msg = f"Error retrieving Jira issue: {str(e)}"
            error_artifact = log_prefix + " Retrieval Failed: " + str(e)
            logger.error(error_msg)
            return error_msg, error_artifact

    @override
    def _run(
        self,
        issue_id: str,
    ) -> Tuple[str, str]:
        """
        Synchronous version of the Jira Issue by ID tool.

        Returns:
            Tuple of Jira issue text and artifact description
        """
        raise NotImplementedError("Use async version of this tool")
