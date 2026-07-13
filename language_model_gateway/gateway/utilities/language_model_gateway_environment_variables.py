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

        return "/usr/src/language_model_gateway/language_model_gateway/gateway/tools/tool_friendly_names.json"

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
    def debug_log_received_oauth_tokens(self) -> bool:
        """Log full requests (headers + body) received by CodingModelRouter.

        Local-development debugging only — lets you inspect exactly what a
        client (e.g. Claude Code's subscription OAuth token, or whether it
        requests streaming) actually sends. Never enable outside local dev;
        this writes bearer tokens and full request bodies to logs in
        plaintext.
        """
        return self.str2bool(os.environ.get("DEBUG_LOG_RECEIVED_OAUTH_TOKENS", "false"))

    @property
    def model_routing_usage_collection_name(self) -> str:
        """Collection name for CodingModelRouter's per-request usage tracking.

        Sibling of mongo_llm_storage_store_collection_name /
        mongo_llm_storage_checkpointer_collection_name (languagemodelcommon),
        but this collection is gateway-specific rather than part of the
        shared persistence factory, so it lives here instead.
        """
        return os.environ.get(
            "MODEL_ROUTING_USAGE_COLLECTION_NAME", "model-router-usage"
        )

    @property
    def model_routing_error_collection_name(self) -> str:
        """Collection name for CodingModelRouter's upstream-failure tracking.

        Sibling of model_routing_usage_collection_name — one document per
        failed upstream request (throttle exhaustion, Bedrock session expiry,
        4xx/5xx upstream responses), for trend-spotting without grepping logs.
        """
        return os.environ.get(
            "MODEL_ROUTING_ERROR_COLLECTION_NAME", "model-router-errors"
        )

    @property
    def model_routing_usage_session_collection_name(self) -> str:
        """Collection name for the per-session usage rollup.

        Sibling of model_routing_usage_collection_name, but one document per
        session_id (upserted on every request) instead of one per request —
        cheap to query for session-level totals (tokens, cost by tier,
        savings) without a $group aggregation over the larger per-request
        collection.
        """
        return os.environ.get(
            "MODEL_ROUTING_USAGE_SESSION_COLLECTION_NAME", "model-router-sessions"
        )

    @property
    def model_routing_usage_session_tracking_enabled(self) -> bool:
        """Whether to upsert the per-session usage rollup at all.

        Independent of the per-request collection (model_routing_usage_collection_name)
        so the two can eventually be toggled separately — e.g. session-only
        tracking once the rollup is trusted to carry the reporting load that
        the per-request collection carries today.
        """
        return self.str2bool(
            os.environ.get("MODEL_ROUTING_USAGE_SESSION_TRACKING_ENABLED", "true")
        )

    @property
    def model_routing_usage_capture_previews(self) -> bool:
        """Whether to write input_preview/output_preview fields to the usage collection.

        Off by default: prompt/response text (even truncated) is
        user/model-generated content, unlike the rest of the usage record
        which is only metadata, so this is an explicit opt-in rather than
        following the tracker's default-enabled posture.
        """
        return self.str2bool(
            os.environ.get("MODEL_ROUTING_USAGE_CAPTURE_PREVIEWS", "false")
        )

    @property
    def model_routing_usage_preview_chars(self) -> int:
        """Max characters of prompt/response text captured per usage record.

        Applies to the input_preview/output_preview fields on
        model_routing_usage_collection_name documents, and only takes effect
        when model_routing_usage_capture_previews is enabled.
        """
        return int(os.environ.get("MODEL_ROUTING_USAGE_PREVIEW_CHARS", "100"))

    @property
    def model_routing_custom_header_prefix(self) -> str:
        """Prefix identifying CodingModelRouter's own custom identity headers.

        Any incoming header whose name starts with this prefix (case
        insensitive) is stripped before forwarding the request upstream to
        Anthropic/Bedrock, and `{prefix}user-id` is used as a best-effort
        usage-attribution fallback when no OIDC-verified identity is present
        (e.g. via Claude Code's ANTHROPIC_CUSTOM_HEADERS). See
        CodingModelRouter._get_auth_info for the trust model.
        """
        return os.environ.get(
            "MODEL_ROUTING_CUSTOM_HEADER_PREFIX", "x-model-routing-"
        ).lower()

    @property
    def model_routing_account_directory_collection_name(self) -> str:
        """Collection name for CodingModelRouter's account_uuid -> email directory.

        Sibling of model_routing_usage_collection_name: the class's own
        constructor default stays the generic "account_directory"; this is
        the app's actual deployed default, more specific and
        collision-resistant for discoverability in a shared database.
        """
        return os.environ.get(
            "MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME",
            "model-router-account-directory",
        )
