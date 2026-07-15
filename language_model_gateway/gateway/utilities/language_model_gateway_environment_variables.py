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

    @property
    def model_routing_bedrock_transport(self) -> str:
        """Which transport CodingModelRouter uses for auth="aws" routes:
        "native" (default) sends requests through Bedrock's own Converse
        API; "mantle" sends them through Bedrock Mantle's OpenAI-compatible
        endpoint instead, using the same model IDs. Originally added as a
        manual, operator-flipped fallback for Bedrock Mantle incidents —
        see docs/superpowers/specs/2026-07-13-native-bedrock-transport-design.md
        — but Mantle's own reliability (bare, undiagnosable
        "internal_server_error" 500s with no detail beyond what's already
        captured) made native the better default once both were proven out;
        "mantle" is now the manual opt-out instead of the default.

        Only the literal value "mantle" (case-insensitive) opts back into
        Mantle — anything else, including unset or a typo, resolves to
        "native" rather than silently landing on the less reliable
        transport.
        """
        return (
            "mantle"
            if os.environ.get("MODEL_ROUTING_BEDROCK_TRANSPORT", "").lower() == "mantle"
            else "native"
        )

    @property
    def model_routing_qwen_enable_thinking(self) -> bool:
        """Whether Qwen routes (`api_type="openai"`) should think before answering.

        Passed to the upstream OpenAI-compatible endpoint as
        `chat_template_kwargs.enable_thinking`. Qwen already emits its
        reasoning as an inline `<think>...</think>` block that
        CodingModelRouter strips from the visible response either way — this
        toggle controls whether that reasoning is generated at all, trading
        answer quality for lower latency/token cost. Defaults to on, matching
        Qwen's own default and this router's behavior before the toggle
        existed.
        """
        return self.str2bool(
            os.environ.get("MODEL_ROUTING_QWEN_ENABLE_THINKING", "true")
        )

    @property
    def model_routing_bedrock_connect_timeout_seconds(self) -> float:
        """Connect timeout (seconds) for the native Bedrock Converse boto3 client.

        botocore defaults this to 60s internally if left unset; passed
        explicitly here so it's tunable via env var instead of a code
        change — see model_routing_bedrock_read_timeout_seconds, the more
        commonly-hit sibling of this timeout for streamed generations.
        """
        return float(
            os.environ.get("MODEL_ROUTING_BEDROCK_CONNECT_TIMEOUT_SECONDS", "60")
        )

    @property
    def model_routing_bedrock_read_timeout_seconds(self) -> float:
        """Read timeout (seconds) for the native Bedrock Converse boto3 client.

        botocore defaults this to 60s internally if left unset. A long
        streamed generation (large max_tokens, slow model) can exceed that
        on a single read and fail with a generic
        "AWSHTTPSConnectionPool ... Read timed out" — raise this via env var
        for routes/models that legitimately need longer than 60s per read,
        rather than hardcoding a larger value for every route.
        """
        return float(os.environ.get("MODEL_ROUTING_BEDROCK_READ_TIMEOUT_SECONDS", "60"))

    @property
    def model_routing_bedrock_max_attempts(self) -> int:
        """Max botocore-level attempts for the native Bedrock Converse client.

        Defaults to 1 (no additional retries at this layer) deliberately,
        mirroring languagemodelcommon's AwsClientFactory.create_bedrock_client
        default — CodingModelRouter already retries transient native-Bedrock
        errors itself with its own backoff (see _throttle_backoff in
        router.py). Raising this stacks botocore's own retry/backoff on top
        of that outer loop.
        """
        return int(os.environ.get("MODEL_ROUTING_BEDROCK_MAX_ATTEMPTS", "1"))

    @property
    def model_routing_bedrock_retry_mode(self) -> str:
        """botocore retry mode for the native Bedrock Converse client.

        Only takes effect if model_routing_bedrock_max_attempts > 1. Mirrors
        AwsClientFactory.create_bedrock_client's own default of "adaptive".
        """
        return os.environ.get("MODEL_ROUTING_BEDROCK_RETRY_MODE", "adaptive")
