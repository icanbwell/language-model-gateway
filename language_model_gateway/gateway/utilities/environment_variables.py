import os
from typing import Optional


class EnvironmentVariables:
    @property
    def github_org(self) -> Optional[str]:
        return os.environ.get("GITHUB_ORGANIZATION_NAME")

    @property
    def github_token(self) -> Optional[str]:
        return os.environ.get("GITHUB_TOKEN")

    @property
    def jira_base_url(self) -> Optional[str]:
        return os.environ.get("JIRA_BASE_URL")

    @property
    def jira_token(self) -> Optional[str]:
        return os.environ.get("JIRA_TOKEN")

    @property
    def jira_username(self) -> Optional[str]:
        return os.environ.get("JIRA_USERNAME")

    @property
    def jwks_uri(self) -> Optional[str]:
        return os.environ.get("JWKS_URI")
