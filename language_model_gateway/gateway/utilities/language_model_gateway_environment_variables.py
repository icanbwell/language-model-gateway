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
    def enable_code_interpreter(self) -> bool:
        return self.str2bool(os.environ.get("ENABLE_CODE_INTERPRETER", "true"))
