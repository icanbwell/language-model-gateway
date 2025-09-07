import logging
from typing import Type, Optional, Tuple, Literal

from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.github.github_pull_request_helper import (
    GithubPullRequestHelper,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class GitHubPullRequestDiffAgentDiffInput(BaseModel):
    """Input model for GitHub Pull Request extraction tool."""

    url: str = Field(
        ...,
        title="Pull Request URL",
        description="URL of the GitHub pull request to analyze",
    )
    use_verbose_logging: Optional[bool] = Field(
        default=False,
        description="Whether to enable verbose logging",
    )


class GitHubPullRequestDiffTool(ResilientBaseTool):
    """
    LangChain-compatible tool for extracting and analyzing GitHub pull requests.
    """

    name: str = "github_pull_request_diff"
    description: str = "Provides a diff of a GitHub pull request given its URL"

    args_schema: Type[BaseModel] = GitHubPullRequestDiffAgentDiffInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    github_pull_request_helper: GithubPullRequestHelper

    def _run(
        self,
        url: Optional[str] = None,
        use_verbose_logging: Optional[bool] = None,
    ) -> Tuple[str, str]:
        """
        Synchronous version of the tool (falls back to async implementation).

        Raises:
            NotImplementedError: Always raises to enforce async usage
        """
        raise NotImplementedError("Use async version of this tool")

    async def _arun(
        self,
        url: Optional[str] = None,
        use_verbose_logging: Optional[bool] = None,
    ) -> Tuple[str, str]:
        """
        Asynchronous version of the GitHub Pull Request extraction tool.

        Returns:
            Tuple of pull request analysis text and artifact description
        """

        assert url, "Pull request URL is required"

        try:
            diff_content: str = (
                await self.github_pull_request_helper.get_pr_diff_content(pr_url=url)
            )
            # Create artifact description
            artifact = f"GitHubPullRequestDiffAgent: Downloaded diff for {url}"
            if use_verbose_logging:
                artifact += f"\n===== Content =====\n```{diff_content}```\n===== End of Content ====="
            return diff_content, artifact

        except Exception as e:
            error_msg = f"Error analyzing GitHub pull requests: {str(e)}"
            error_artifact = "GitHubPullRequestDiffAgent: Analysis failed"
            logger.error(error_msg)
            return error_msg, error_artifact
