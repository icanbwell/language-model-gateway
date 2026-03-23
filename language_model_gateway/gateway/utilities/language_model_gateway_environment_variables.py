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
    def mongo_db_token_collection_name(self) -> Optional[str]:
        return os.environ.get("MONGO_DB_TOKEN_COLLECTION_NAME")

    @property
    def mcp_tools_metadata_cache_timeout_seconds(self) -> int:
        return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS", 3600))

    @property
    def mcp_tools_metadata_cache_ttl_seconds(self) -> int:
        return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TTL_SECONDS", 3600))

    @property
    def tool_output_token_limit(self) -> Optional[int]:
        limit = os.environ.get("TOOL_OUTPUT_TOKEN_LIMIT")
        return int(limit) if limit and limit.isdigit() else None

    @property
    def tool_call_timeout_seconds(self) -> int:
        """Timeout in seconds for tool calls."""
        return int(os.environ.get("TOOL_CALL_TIMEOUT_SECONDS", "600"))

    @property
    def app_login_uri(self) -> str:
        value = os.environ.get("APP_LOGIN_URI")
        return value if value else "/app/login"

    @property
    def app_token_save_uri(self) -> str:
        value = os.environ.get("APP_TOKEN_SAVE_URI")
        return value if value else "/app/token"

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
