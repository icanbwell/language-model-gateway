import os
from typing import Optional

from moto.utilities.utils import str2bool


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
    def auth_algorithms(self) -> Optional[list[str]]:
        auth_algorithms: str | None = os.environ.get("AUTH_ALGORITHMS")
        return auth_algorithms.split(",") if auth_algorithms else None

    @property
    def auth_redirect_uri(self) -> Optional[str]:
        return os.environ.get("AUTH_REDIRECT_URI")

    @property
    def mongo_uri(self) -> Optional[str]:
        return os.environ.get("MONGO_URL")

    @property
    def mongo_db_name(self) -> Optional[str]:
        return os.environ.get("MONGO_DB_NAME")

    @property
    def mongo_db_auth_cache_collection_name(self) -> Optional[str]:
        return os.environ.get("MONGO_DB_AUTH_CACHE_COLLECTION_NAME")

    @property
    def mongo_db_token_collection_name(self) -> Optional[str]:
        return os.environ.get("MONGO_DB_TOKEN_COLLECTION_NAME")

    @property
    def mcp_tools_metadata_cache_timeout_seconds(self) -> int:
        return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS", 3600))

    @property
    def mcp_tools_metadata_cache_ttl_seconds(self) -> int:
        return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TTL_SECONDS", 3600))

    @property
    def oauth_cache(self) -> str:
        return os.environ.get("OAUTH_CACHE", "memory")

    @property
    def auth_providers(self) -> Optional[list[str]]:
        auth_providers: str | None = os.environ.get("AUTH_PROVIDERS")
        return auth_providers.split(",") if auth_providers else None

    @staticmethod
    def str2bool(v: str | None) -> bool:
        return v is not None and str(v).lower() in ("yes", "true", "t", "1", "y")

    @property
    def mongo_db_cache_disable_delete(self) -> Optional[bool]:
        return str2bool(os.environ.get("MONGO_DB_AUTH_CACHE_DISABLE_DELETE"))

    @property
    def override_email(self) -> Optional[str]:
        return os.environ.get("OVERRIDE_EMAIL")
