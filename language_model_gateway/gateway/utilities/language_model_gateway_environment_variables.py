import os
from typing import Optional

from oidcauthlib.utilities.environment.environment_variables import EnvironmentVariables


class LanguageModelGatewayEnvironmentVariables(EnvironmentVariables):
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
    def enable_llm_memory(self) -> bool:
        return self.str2bool(os.environ.get("ENABLE_LLM_MEMORY", "false"))

    @property
    def llm_storage_type(self) -> str:
        return os.environ.get("LLM_STORAGE_TYPE", "memory")

    @property
    def mongo_llm_storage_uri(self) -> Optional[str]:
        return os.environ.get("MONGO_LLM_STORAGE_URI") or self.mongo_uri

    @property
    def mongo_llm_storage_db_name(self) -> Optional[str]:
        return os.environ.get("MONGO_LLM_STORAGE_DB_NAME", "llm_storage")

    @property
    def mongo_llm_storage_db_username(self) -> Optional[str]:
        return os.environ.get("MONGO_LLM_STORAGE_DB_USERNAME") or self.mongo_db_username

    @property
    def mongo_llm_storage_db_password(self) -> Optional[str]:
        return os.environ.get("MONGO_LLM_STORAGE_DB_PASSWORD") or self.mongo_db_password

    @property
    def mongo_llm_storage_store_collection_name(self) -> str:
        return os.environ.get("MONGO_LLM_STORAGE_STORE_COLLECTION_NAME", "stores")

    @property
    def mongo_llm_storage_checkpointer_collection_name(self) -> str:
        return os.environ.get(
            "MONGO_LLM_STORAGE_CHECKPOINTER_COLLECTION_NAME", "checkpoints"
        )

    @property
    def enable_llm_store(self) -> bool:
        return self.str2bool(os.environ.get("ENABLE_LLM_STORE", "false"))

    @property
    def enable_llm_checkpointer(self) -> bool:
        return self.str2bool(os.environ.get("ENABLE_LLM_CHECKPOINTER", "false"))
