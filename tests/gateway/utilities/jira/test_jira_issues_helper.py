import json
import os
from datetime import datetime, timezone
from os import makedirs, path
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Optional, Any

import pytest
from pytest_httpx import HTTPXMock

from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)
from language_model_gateway.gateway.utilities.jira.JiraIssuesPerAssigneeInfo import (
    JiraIssuesPerAssigneeInfo,
)
from language_model_gateway.gateway.utilities.jira.jira_issue import JiraIssue
from language_model_gateway.gateway.utilities.jira.jira_issue_result import (
    JiraIssueResult,
)
from language_model_gateway.gateway.utilities.jira.jira_issues_helper import (
    JiraIssueHelper,
)
from tests.gateway.mocks.mock_environment_variables import MockEnvironmentVariables


@pytest.mark.httpx_mock(
    should_mock=lambda request: os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1"
)
async def test_jira_get_summarized_issues(httpx_mock: HTTPXMock) -> None:
    print()
    data_dir: Path = Path(__file__).parent.joinpath("./")
    temp_folder = data_dir.joinpath("./temp")
    if path.isdir(temp_folder):
        rmtree(temp_folder)
    makedirs(temp_folder)

    max_projects = 2

    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        os.environ["JIRA_USERNAME"] = "dummy_username"
        jira_base_url: str = "https://icanbwell.atlassian.net"
        access_token: Optional[str] = "fake_token"
        test_container.register(
            EnvironmentVariables, lambda c: MockEnvironmentVariables()
        )

        # Mock Jira search API response
        search_url = f"{jira_base_url}/rest/api/3/search/jql"
        sample_issues_content: Dict[str, Any] = {
            "total": 2,
            "issues": [
                {
                    "key": "PROJECT-1",
                    "self": "http://foo/PROJECT-1",
                    "fields": {
                        "summary": "First test issue",
                        "status": {"name": "Closed"},
                        "created": "2024-09-01T00:00:00.000Z",
                        "resolutiondate": "2024-09-02T00:00:00.000Z",
                        "assignee": {"displayName": "user1"},
                        "project": {"key": "PROJECT"},
                    },
                },
                {
                    "key": "PROJECT-2",
                    "self": "http://foo/PROJECT-2",
                    "fields": {
                        "summary": "Second test issue",
                        "status": {"name": "Closed"},
                        "created": "2024-09-01T00:00:00.000Z",
                        "resolutiondate": "2024-09-02T00:00:00.000Z",
                        "assignee": {"displayName": "user2"},
                        "project": {"key": "PROJECT"},
                    },
                },
            ],
        }

        httpx_mock.add_response(
            url=search_url,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AsyncJiraIssueHelper",
            },
            content=json.dumps(sample_issues_content).encode(),
            status_code=200,
        )
    else:
        # Get credentials from environment variables
        jira_base_url = os.getenv("JIRA_BASE_URL", "")
        access_token = os.getenv("JIRA_TOKEN")

    if not jira_base_url or not access_token:
        raise ValueError(
            "Please set JIRA_BASE_URL and JIRA_TOKEN environment variables"
        )

    http_client_factory = HttpClientFactory()

    # Initialize Jira Issue Helper
    issue_helper = JiraIssueHelper(
        jira_base_url=jira_base_url,
        access_token=access_token,
        http_client_factory=http_client_factory,
        username=os.environ["JIRA_USERNAME"],
    )
    max_issues = 2

    # Get issue counts with optional parameters
    jira_issue_result: JiraIssueResult = await issue_helper.retrieve_closed_issues(
        max_projects=max_projects,  # Optional: limit projects
        max_issues=max_issues,  # Optional: limit issues
        min_created_at=datetime(
            2024, 9, 1, tzinfo=timezone.utc
        ),  # Optional: minimum created date
        include_full_description=True,
    )
    issues: List[JiraIssue] = jira_issue_result.issues

    assert jira_issue_result.error is None

    assert len(issues) > 0, jira_issue_result.error

    print("========== Issues ========")
    for issue in issues:
        print(issue)
    print("==========================")

    issue_counts: Dict[str, JiraIssuesPerAssigneeInfo] = (
        issue_helper.summarize_issues_by_assignee(issues=issues)
    )

    # Assertions
    assert len(issue_counts) > 0
    assert len(issues) == max_issues

    # Export results
    issue_helper.export_results(
        issue_counts=issue_counts,
        output_file=str(
            temp_folder.joinpath("issue_counts.tsv")
        ),  # Optional TSV export
    )

    # Verify export file was created
    assert path.exists(temp_folder.joinpath("issue_counts.tsv"))
