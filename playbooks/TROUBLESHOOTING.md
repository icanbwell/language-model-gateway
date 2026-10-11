# Troubleshooting

Last verified: 2026-10-11 against b0d7252b by Claude

First checks for symptoms in this repo. Where to look for the signals is in [MONITORING.md](MONITORING.md). Confirm the service is deployed before investigating production (see [README.md](README.md)).

## Reading signals correctly

- A failed HTTP request writes two ERROR messages (request and response) from `FastApiLoggingMiddleware`; count requests, not lines.
- Each log record is one JSON line; a traceback is folded into the `exception` field, so line counts equal record counts (`log_levels.py`).
- A gateway 5xx may originate upstream (model provider or MCP server); the response body text is in the `Response ERROR` message.

## Come here if you're seeing errors or a 4xx/5xx from `/api/v1/chat/completions`

**Signal:** `Response ERROR` messages in the namespace, or a caller-side error.
**First checks:** (1) `GET /health` returns `OK`. (2) Read the `Response ERROR` message for status and elapsed time. (3) Check `AUTH` and `TOKEN_EXCHANGE` logger lines for token failures (`AUTH_*` and Okta/OIDC settings, `oidcauthlib`). (4) Check the model config id exists in the loaded configuration (configs load at startup; restart required to pick up changes). (5) Check the upstream provider: the `LLM` and `MCP` loggers.
**Likely causes:** unknown model id; expired or missing token; upstream provider error; MCP server unreachable (all suspected, not verified against incidents).
**Action:** fix config in `language-model-gateway-configuration` or escalate to the owning team.
**Do not:** enable `HTTP_TRACING_LOG_LEVEL=DEBUG` in a shared environment without need: it logs request headers and bodies (see [LOGGING.md](LOGGING.md)).

## Come here if the model invents tool results / lists records it cannot have

**Signal:** assistant text naming records, medications, care team members or tool-call markup (`<call_tool>`, `<search_tools>`) with no tool message in the conversation.
**First checks:**
1. Is the caller Bailey? If so the record tools are bound by baileyai, not here; follow [baileyai's playbook](https://github.com/icanbwell/baileyai/tree/main/playbooks) (Groundcover workload `baileyai`, tool-resolution phrases, `pseudo_tool_call_detected_total`, `ToolAvailabilityStep`, `bailey_messages` lookup). This repo contains none of those log phrases, the metric or the step (searched `origin/main`).
2. For a model served by this gateway: check whether the config sets `use_tool_discovery` (`language_model_gateway/config_schema.json`). When true, the model gets only the meta-tools `search_tools` and `call_tool` (`langchain_chat_completions_provider.py` imports `SearchToolsTool` and `CallToolTool` from `languagemodelcommon`) and must discover real tools through them; when it is not set, the config's declared MCP tools are loaded directly. Confirm which mode the config used and which tools were bound for the turn from the `MCP` logger lines.
3. The skills prompt `language-model-gateway-configs/chat_completions/prompts/skills.md` instructs the model to write `search_tools(...)` and `call_tool(...)` calls; a model with no such tools bound can emit them as plain text.
**Likely causes:** tools not bound for the turn (suspected); tool catalog fetch failed (suspected). The gateway-side behavior on a failed tool catalog fetch is unverified.
**Action:** report to the caller's owning team with the conversation id and time window, never message content.
**Do not:** copy message content into tickets or chat.

## Come here if config changes do not take effect

**Signal:** a new or edited model config is not listed by `GET /api/v1/models`.
**First checks:** configs and MCP tool schemas are cached (`CACHING.md`: `CONFIG_CACHE_TIMEOUT_SECONDS`, `SNAPSHOT_CACHE_TTL_SECONDS`); restart the service to pick up configuration changes.
**Action:** restart after the config change is deployed.

## Escalation

Owning team: bAIley team (unverified; no owner is named in this repo; `CODEOWNERS` lists only Enterprise Architecture for `AGENTS.md`). Bring the namespace, time window, and request or conversation ids, never PHI.
