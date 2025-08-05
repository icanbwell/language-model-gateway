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
    def auth_jwks_uri(self) -> Optional[str]:
        return os.environ.get("AUTH_JWKS_URI")

    @property
    def auth_audience(self) -> Optional[str]:
        return os.environ.get("AUTH_AUDIENCE")

    @property
    def auth_issuer(self) -> Optional[str]:
        return os.environ.get("AUTH_ISSUER")

    @property
    def auth_algorithms(self) -> Optional[list[str]]:
        auth_algorithms: str | None = os.environ.get("AUTH_ALGORITHMS")
        return auth_algorithms.split(",") if auth_algorithms else None

    @property
    def auth_well_known_uri(self) -> Optional[str]:
        return os.environ.get("AUTH_WELL_KNOWN_URI")
