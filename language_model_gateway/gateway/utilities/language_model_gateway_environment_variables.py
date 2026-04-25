import os
from typing import Optional


from languagemodelcommon.utilities.environment.language_model_common_environment_variables import (
    LanguageModelCommonEnvironmentVariables,
)


class LanguageModelGatewayEnvironmentVariables(LanguageModelCommonEnvironmentVariables):
    @property
    def github_org(self) -> Optional[str]:
        return os.environ.get("GITHUB_ORGANIZATION_NAME")

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
    def system_commands(self) -> list[str]:
        system_commands: str | None = os.environ.get("SYSTEM_COMMANDS", "clear tokens")
        return system_commands.split(",") if system_commands else []

    @property
    def do_not_pass_through_headers(self) -> set[str]:
        raw_value = os.environ.get(
            "DO_NOT_PASS_THROUGH_HEADERS",
            "connection,keep-alive,proxy-authenticate,proxy-authorization,te,trailers,transfer-encoding,upgrade,host,content-length,authorization",
        )
        if raw_value:
            return set(
                item.strip().lower() for item in raw_value.split(",") if item.strip()
            )
        else:
            return set()

    @property
    def tool_friendly_name_config_path(self) -> str:
        configured = os.environ.get("TOOL_FRIENDLY_NAME_CONFIG_PATH")
        if configured and configured.strip():
            return configured

        return "/usr/src/language_model_gateway/gateway/tools/tool_friendly_names.json"

    @property
    def allowed_origins(self) -> list[str]:
        raw = os.environ.get("ALLOWED_ORIGINS", "")
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        return origins if origins else ["*"]

    @property
    def help_keywords(self) -> list[str]:
        raw = os.environ.get("HELP_KEYWORDS", "help")
        return raw.split(";") if raw else ["help"]

    @property
    def scraping_bee_api_key(self) -> Optional[str]:
        return os.environ.get("SCRAPING_BEE_API_KEY")

    @property
    def google_api_key(self) -> Optional[str]:
        return os.environ.get("GOOGLE_API_KEY")

    @property
    def google_cse_id(self) -> Optional[str]:
        return os.environ.get("GOOGLE_CSE_ID")

    @property
    def provider_search_api_url(self) -> Optional[str]:
        return os.environ.get("PROVIDER_SEARCH_API_URL")

    @property
    def github_maximum_repos(self) -> int:
        return int(os.environ.get("GITHUB_MAXIMUM_REPOS", "100"))

    @property
    def github_maximum_pull_requests_per_repo(self) -> int:
        return int(os.environ.get("GITHUB_MAXIMUM_PULL_REQUESTS_PER_REPO", "100"))

    @property
    def jira_maximum_projects(self) -> int:
        return int(os.environ.get("JIRA_MAXIMUM_PROJECTS", "100"))

    @property
    def jira_maximum_issues_per_project(self) -> int:
        return int(os.environ.get("JIRA_MAXIMUM_ISSUES_PER_PROJECT", "100"))

    @property
    def openai_agent_url(self) -> Optional[str]:
        return os.environ.get("OPENAI_AGENT_URL")

    @property
    def databricks_host(self) -> Optional[str]:
        return os.environ.get("DATABRICKS_HOST")

    @property
    def databricks_token(self) -> Optional[str]:
        return os.environ.get("DATABRICKS_TOKEN")

    @property
    def databricks_sql_warehouse_id(self) -> Optional[str]:
        return os.environ.get("DATABRICKS_SQL_WAREHOUSE_ID")

    @property
    def config_refresh_interval_minutes(self) -> int:
        return int(os.environ.get("CONFIG_REFRESH_INTERVAL_MINUTES", "60"))

    @property
    def auth_plugin_names(self) -> list[str]:
        """Comma-separated plugin names to query for OAuth provider recovery."""
        raw = os.environ.get("AUTH_PLUGIN_NAMES", "")
        return [n.strip() for n in raw.split(",") if n.strip()]
