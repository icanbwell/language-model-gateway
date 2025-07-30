import os
from os import makedirs, path
from pathlib import Path
from shutil import rmtree
from typing import Optional

import httpx
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
from language_model_gateway.gateway.utilities.github.github_pull_request_helper import (
    GithubPullRequestHelper,
)
from tests.gateway.mocks.mock_environment_variables import MockEnvironmentVariables


@pytest.mark.httpx_mock(
    should_mock=lambda request: os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1"
)
async def test_github_get_pull_request_diff(
    async_client: httpx.AsyncClient, httpx_mock: HTTPXMock
) -> None:
    print()
    data_dir: Path = Path(__file__).parent.joinpath("./")
    temp_folder = data_dir.joinpath("./temp")
    if path.isdir(temp_folder):
        rmtree(temp_folder)
    makedirs(temp_folder)

    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        org_name: str = "icanbwell"
        access_token: Optional[str] = "fake_token"
        test_container.register(
            EnvironmentVariables, lambda c: MockEnvironmentVariables()
        )
        sample_diff_content = """diff --git a/configs/chat_completions/testing/searchmining_claudehaiku3.json b/configs/chat_completions/testing/searchmining_claudehaiku3.json
new file mode 100644
index 0000000..8c5c589
--- /dev/null
+++ b/configs/chat_completions/testing/searchmining_claudehaiku3.json
@@ -0,0 +1,53 @@
+{
+   "$schema": "https://raw.githubusercontent.com/imranq2/language_model_gateway/main/language_model_gateway/configs/config_schema.json",
+   "id": "search_mining_claude_haiku3",
+   "name": "Search Mining Claude Haiku3",
+   "description": "Specialized Anthropic LLM configuration for processing NPI records and identifying organizational affiliations with high precision and cost efficiency.",
+   "owner": "Kenan Spruill",
+   "model": {
+     "provider": "bedrock",
+     "model": "us.anthropic.claude-3-haiku-20240307-v1:0"
+   },
+   "system_prompts": [
+     {
+       "role": "system",
+       "content": "You are an AI assistant focused on providing accurate and precise information. Prioritize factual, verifiable information and avoid speculation or unsubstantiated claims. Let’s think step by step and take your time to get the right answer."
+     }
+   ],
+   "model_parameters": [
+     {
+       "key": "temperature",
+       "value": 0
+     },
+     {
+       "key": "top_p",
+       "value": 0.1
+     },
+     {
+       "key": "max_tokens",
+       "value": 4000
+     }
+   ],
+   "headers": [
+     {
+       "key": "Authorization",
+       "value": "Bearer OPENAI_API_KEY"
+     }
+   ],
+   "example_prompts": [
+     {
+       "role": "user",
+       "content": "Within this block of text, extract organizational affiliations for NPI 1234567890 with specialty in cardiology in California"
+     },
+     {
+       "role": "user",
+       "content": "Using this block of text, validate hospital connections for John Smith a pediatric surgeon in Chicago"
+     },
+     {
+       "role": "user",
+       "content": "Find primary workplace for a dermatologist with NPI number 1876543210 from this block of text."
+     }
+
+
+   ]
+}
diff --git a/configs/chat_completions/testing/searchmining_llama3B.json b/configs/chat_completions/testing/searchmining_llama3B.json
new file mode 100644
index 0000000..ad46c5c
--- /dev/null
+++ b/configs/chat_completions/testing/searchmining_llama3B.json
@@ -0,0 +1,53 @@
+{
+   "$schema": "https://raw.githubusercontent.com/imranq2/language_model_gateway/main/language_model_gateway/configs/config_schema.json",
+   "id": "search_mining_llama3B",
+   "name": "Search Mining Llama3B",
+   "description": "Specialized Meta LLM configuration for processing NPI records and identifying organizational affiliations with high precision and cost efficiency.",
+   "owner": "Kenan Spruill",
+   "model": {
+     "provider": "bedrock",
+     "model": "us.meta.llama3-2-3b-instruct-v1:0"
+   },
+   "system_prompts": [
+     {
+       "role": "system",
+       "content": "You are an AI assistant focused on providing accurate and precise information. Prioritize factual, verifiable information and avoid speculation or unsubstantiated claims. Let’s think step by step and take your time to get the right answer."
+     }
+   ],
+   "model_parameters": [
+     {
+       "key": "temperature",
+       "value": 0
+     },
+     {
+       "key": "top_p",
+       "value": 0.1
+     },
+     {
+       "key": "max_tokens",
+       "value": 4000
+     }
+   ],
+   "headers": [
+     {
+       "key": "Authorization",
+       "value": "Bearer OPENAI_API_KEY"
+     }
+   ],
+   "example_prompts": [
+     {
+       "role": "user",
+       "content": "Within this block of text, extract organizational affiliations for NPI 1234567890 with specialty in cardiology in California"
+     },
+     {
+       "role": "user",
+       "content": "Using this block of text, validate hospital connections for John Smith a pediatric surgeon in Chicago"
+     },
+     {
+       "role": "user",
+       "content": "Find primary workplace for a dermatologist with NPI number 1876543210 from this block of text."
+     }
+
+
+   ]
+}
    """

        # Mock the GitHub API responses for PR details and diff
        httpx_mock.add_response(
            url=f"https://api.github.com/repos/{org_name}/language-model-gateway-configuration/pulls/6",
            method="GET",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3.diff",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "AsyncGithubPullRequestHelper",
            },
            content=sample_diff_content.encode(),
            status_code=200,
        )
    else:
        # Get credentials from environment variables
        org_name = "icanbwell"  # os.getenv('GITHUB_ORG')
        access_token = os.getenv("GITHUB_TOKEN")

        if not org_name or not access_token:
            raise ValueError(
                "Please set GITHUB_ORG and GITHUB_TOKEN environment variables"
            )

    http_client_factory = HttpClientFactory()

    # Initialize PR counter
    pr_counter = GithubPullRequestHelper(
        org_name=org_name,
        access_token=access_token,
        http_client_factory=http_client_factory,
    )

    diff: str = await pr_counter.get_pr_diff_content(
        pr_url=f"https://github.com/{org_name}/language-model-gateway-configuration/pull/6/"
    )
    print(diff)
    assert "search_mining_claude_haiku3" in diff
