# CodingModelRouter

Routes Anthropic Messages API requests to **Claude models** (via Anthropic API
passthrough) or **AWS Bedrock models** (Qwen, or Bedrock-hosted Claude) based on
a JSON config keyed by model name.

---

## Overview

`CodingModelRouter` is a FastAPI router that proxies requests arriving in the
Anthropic Messages API wire format.  Clients (e.g. Claude Code, Claude Desktop,
the Anthropic SDK) point their `ANTHROPIC_BASE_URL` at this gateway and send
requests exactly as they would to `api.anthropic.com`.  The router:

1. Reads the `model` field from the request body.
2. Looks up the model name in a local route config file.
3. Forwards the request to the configured upstream — either Anthropic's API
   (for Claude models) or AWS Bedrock (for Qwen or Bedrock-hosted Claude).
4. Streams the response back verbatim, or translates it when the upstream
   speaks OpenAI Chat Completions format.

The current production config uses a **tier-based routing model**:

| Tier     | Client model (exact) | Client model (pattern) | Upstream                     | Backend model                |
|----------|-----------------------|-------------------------|-------------------------------|-------------------------------|
| `haiku`  | `claude-haiku-4-5-*`  | `^claude-haiku-`        | AWS Bedrock (OpenAI-compat)   | Qwen3-Coder-30B (fast/cheap)  |
| `sonnet` | `claude-sonnet-5`     | `^claude-sonnet(-\|$)`  | AWS Bedrock (OpenAI-compat)   | Qwen3-Coder-next (capable)    |
| `opus`   | `claude-opus-4-8`     | `^claude-opus-`         | Anthropic API (passthrough)   | Claude Opus 4.8               |
| `fable`  | `claude-fable-5`      | `^claude-fable-`        | Anthropic API (passthrough)   | Claude Fable 5                |

Haiku and Sonnet requests are handled by Bedrock Qwen models (lower cost, 262k
context).  Opus and Fable requests are forwarded unchanged to Anthropic —
the client's `Authorization` header is used directly, so no API key is needed
at the gateway level for those tiers.

Each tier also has a `claude_model_pattern` regex (see schema below) so a
Claude model *version bump* (e.g. `claude-sonnet-4-6` → `claude-sonnet-5` →
`claude-sonnet-6`) keeps routing correctly without a config change — the
exact `claude_model` key is only the fast-path/documentation value, matched
first; the pattern is the fallback that keeps old *and* new ids working.
Only a genuinely new tier needs a new route entry. This is a
recurrence-prevention fix for an incident where the exact-match-only sonnet
route silently fell back to Anthropic direct after Claude Code's default
model id changed, bypassing cost-routing and context-budget enforcement with
no visible symptom until a real context-length error surfaced downstream,
confusingly unrelated to the actual root cause.

---

## Registered endpoints

| Method | Path                        | Description                              |
|--------|-----------------------------|------------------------------------------|
| `POST` | `/v1/messages`              | Proxy Anthropic Messages API             |
| `POST` | `/v1/messages/count_tokens` | Proxy Anthropic token-count endpoint     |

For `api_type: openai` routes, `/v1/messages/count_tokens` is not forwarded
upstream; the router returns a rough estimate (`len(body_json) / 4`) instead.

---

## Environment variables

| Variable        | Default                                    | Description                                      |
|-----------------|--------------------------------------------|--------------------------------------------------|
| `ROUTER_CONFIG` | `<package>/gateway/routers/model_routing/model-router-config.json` | Path to the route config JSON file (defaults to the file bundled in the Python package) |
| `AWS_PROFILE`   | *(none)*                                                           | AWS profile used when signing Bedrock requests                                          |
| `DEBUG_LOG_RECEIVED_OAUTH_TOKENS` | `false` | Logs the full request (method, path, headers, body) received on `/v1/messages` at WARNING level, so you can inspect exactly what a client sends — e.g. whether Claude Code's subscription OAuth token is a JWT or an opaque string, or whether it requests `"stream": true`. **Local development only — never enable in a shared or deployed environment**; this writes bearer tokens and full request bodies to logs in plaintext. |
| `MONGO_LLM_STORAGE_URI` (falls back to `MONGO_URL`) | *(none)* | MongoDB connection string used for usage tracking (see "Usage tracking" below). If unset, usage tracking is disabled entirely. |
| `MONGO_LLM_STORAGE_DB_NAME` | `llm_storage` | Database name for the usage-tracking collection. |
| `MODEL_ROUTING_USAGE_COLLECTION_NAME` | `model-router-usage` | Collection name for per-request usage-tracking records within that database. |
| `MODEL_ROUTING_USAGE_SESSION_COLLECTION_NAME` | `model-router-sessions` | Collection name for the per-session usage rollup (see "Session rollup" below). |
| `MODEL_ROUTING_USAGE_SESSION_TRACKING_ENABLED` | `true` | Independent on/off switch for the session rollup, separate from per-request tracking — set to `false` to stop writing `MODEL_ROUTING_USAGE_SESSION_COLLECTION_NAME` while per-request tracking keeps running (or vice versa, once/if per-request tracking gets its own switch). |
| `MODEL_ROUTING_USAGE_CAPTURE_PREVIEWS` | `false` | Opt-in: write truncated `input_preview`/`output_preview` fields (see "Usage tracking" below). Off by default because, unlike the rest of the record, previews persist actual prompt/response content. |
| `MODEL_ROUTING_USAGE_PREVIEW_CHARS` | `100` | Max characters kept in `input_preview`/`output_preview` when previews are enabled. |
| `MODEL_ROUTING_CUSTOM_HEADER_PREFIX` | `x-model-routing-` | Any incoming header under this prefix (case-insensitive) is (a) stripped before forwarding upstream and (b) captured into the usage record's `custom_headers` field. `{prefix}user-id` is additionally used as a best-effort `user_id` fallback — see "Usage tracking" below. |
| `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` | `model-router-account-directory` | Collection name for the manually-populated account_uuid → email lookup table (see "Usage tracking" below). |
| `MODEL_ROUTING_ERROR_COLLECTION_NAME` | `model-router-errors` | Collection name for upstream-failure tracking (see "Error tracking" below). |
| `MONGO_LLM_STORAGE_DB_USERNAME` / `MONGO_LLM_STORAGE_DB_PASSWORD` (fall back to `MONGO_DB_USERNAME` / `MONGO_DB_PASSWORD`) | *(none)* | Merged into the connection string above if the URI has no embedded credentials. |
| `LOG_FORMAT` (gateway-wide, not router-specific) | `json` | Set to `text` to use the plain-text log format instead of single-line JSON (`language_model_gateway/gateway/utilities/logger/log_levels.py`). JSON is required for Groundcover to parse each log line correctly. |

The config file lives at
`language_model_gateway/gateway/routers/model_routing/model-router-config.json`
and is bundled into the Docker image as part of the normal Python source copy.
No separate volume mount or `ROUTER_CONFIG` env var is required.

---

## Route config file

The config file is a JSON object with a `routes` array.  Each entry maps a
Claude model name (as sent by the client) to an upstream destination.

### Schema

```jsonc
{
  "routes": [
    {
      // Required fields
      "claude_model": "claude-sonnet-5",     // model name the client sends (exact match, checked first)
      "url":          "https://...",          // upstream URL
      "model":        "upstream-model-id",   // model name forwarded to upstream (aws/openai routes only — see note below)
      "auth":         "passthrough" | "aws", // auth strategy (see below)

      // Optional routing metadata
      "claude_model_pattern": "^claude-sonnet(-|$)", // regex fallback checked when claude_model doesn't match exactly;
                                              // keeps routing correct across Claude model version bumps (old and new
                                              // ids both match) without needing a config change per bump
      "tier":         "haiku" | "sonnet" | "opus" | "fable", // logical tier label (informational)
      "api_type":     "anthropic" | "openai", // wire protocol (default: "anthropic")
      "aws_region":   "us-east-1",            // AWS region for Bedrock (default: "us-east-1")
      "price_per_mtok": 0.5,                  // actual backend cost per million tokens (used to compute cost_usd; not enforced as a limit)
      "anthropic_price_per_mtok": 3.0,        // what claude_model would cost at Anthropic's own list price — baseline for cost_savings_usd (see "Usage tracking" below)

      // Context budget fields (openai routes only — controls Qwen token counting and compression)
      "context_window":             262144,   // advertised context window returned to the client
      "backend_max_context_tokens": 262144,   // actual backend limit used for budget math
      "reserved_output_tokens":     32768,    // tokens reserved for output; caps max_tokens and reduces input budget
      "tokenizer_safety_margin":    4096,     // extra headroom subtracted from input budget to absorb estimation error
      "max_tokens":                 32768,    // default max_tokens cap applied when the client doesn't send one
      "tokenizer_model":  "Qwen/Qwen3-Coder-30B-A3B-Instruct"
                                              // HuggingFace model ID for accurate preflight token counting
    }
  ]
}
```

**Effective input budget formula** (for `api_type: openai` routes):

```
effective_input_tokens = backend_max_context_tokens
                       - reserved_output_tokens
                       - tokenizer_safety_margin
```

Example with the default Sonnet route:
`262144 − 32768 − 4096 = 225280 tokens` available for input (system prompt + history + tools).

If the config file is not found, the router logs a warning and falls back to
Anthropic direct for all requests.

If a model is not listed in `routes` (no exact or pattern match), the router
also falls back to Anthropic direct, forwarding the client's `Authorization`
header unchanged — but this is now logged at **ERROR** (not warning) and, if
the fallback request then errors upstream, the error body returned to the
client is annotated with a note that the request had no configured route, so
a confusing downstream symptom (e.g. a context-length error) is traceable
back to the actual root cause instead of looking unrelated.

### Auth strategies

| Value         | Behaviour                                                                               |
|---------------|-----------------------------------------------------------------------------------------|
| `passthrough` | Forwards the client's `Authorization` header, and the client's exact requested model id (not the configured `model` value), to the upstream as-is (Anthropic direct). |
| `aws`         | Signs each request with AWS SigV4 (for Bedrock); forwards the configured `model` value, since that's a genuinely different backend model id. No auth header is forwarded. |

### API types

| Value       | Behaviour                                                                                           |
|-------------|-----------------------------------------------------------------------------------------------------|
| `anthropic` | Upstream speaks Anthropic Messages API; bytes are forwarded verbatim.                              |
| `openai`    | Upstream speaks OpenAI Chat Completions API (e.g. Bedrock Mantle); request is translated from Anthropic format and response translated back. |

---

## Example configs

### Anthropic direct passthrough

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://api.anthropic.com/v1/messages",
      "model":        "claude-sonnet-4-6",
      "auth":         "passthrough"
    }
  ]
}
```

### AWS Bedrock — Anthropic format

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-5-sonnet-20241022-v2:0/invoke",
      "model":        "anthropic.claude-3-5-sonnet-20241022-v2:0",
      "auth":         "aws",
      "api_type":     "anthropic",
      "aws_region":   "us-east-1"
    }
  ]
}
```

### AWS Bedrock — OpenAI-compatible endpoint (Bedrock Mantle)

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://bedrock-runtime.us-east-1.amazonaws.com/v1/chat/completions",
      "model":        "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
      "auth":         "aws",
      "api_type":     "openai",
      "aws_region":   "us-east-1"
    }
  ]
}
```

---

## Request translation (`api_type: openai`)

When `api_type` is `openai`, the router translates the Anthropic request body
to OpenAI Chat Completions format before forwarding, and translates the
response back to Anthropic format before returning it to the client.

Translated fields:

| Anthropic request field      | OpenAI equivalent                   |
|------------------------------|-------------------------------------|
| `system`                     | `messages[0]` with `role: system`   |
| `messages[].content[]` (text)| `messages[].content` (string)       |
| `messages[].content[]` (image)| `messages[].content[].image_url`   |
| `messages[].content[]` (tool_use) | `messages[].tool_calls`        |
| `messages[].content[]` (tool_result) | `messages[]` with `role: tool` |
| `tools[].input_schema`       | `tools[].function.parameters`       |
| `tool_choice: any`           | `tool_choice: required`             |

Thinking blocks (`<think>…</think>`) emitted by reasoning models are stripped
from both streaming and non-streaming responses before they are returned to the
client.

---

## Throttle retry and backoff

For `auth: aws` routes, the router automatically retries on throttling
responses (HTTP 429 or bodies matching common Bedrock throttle messages):

| Parameter           | Value                 |
|---------------------|-----------------------|
| Max retries         | 5                     |
| Base delay          | 1 s                   |
| Max delay           | 20 s                  |
| Backoff             | Exponential with jitter |
| Dispatch pacing     | 300 ms minimum between requests |

Context-overflow errors (Bedrock reports that the prompt exceeds the model's
context window) are not retried and are surfaced immediately.  For
`api_type: openai` streaming requests, the router additionally halves
`max_tokens` up to four times before giving up.

---

## Error handling

Upstream errors (4xx/5xx) are returned to the client with the original status
code and body — except for unmatched-model fallback requests (see "Auth
strategies" above), where the error body's `error.message` is prefixed with a
note identifying the missing route as the likely root cause.

AWS credential errors (`TokenRetrievalError`) and other infrastructure errors
are surfaced as a valid Anthropic assistant message with `stop_reason:
end_turn`, so that streaming clients receive a well-formed response rather than
a broken stream.  The error text is included in the assistant message content
to aid debugging.

---

## Streaming reliability

Per the [gateway protocol reference](https://code.claude.com/docs/en/llm-gateway-protocol):
"Inference responses must stream... a gateway that buffers complete responses
before relaying them stalls the client." The router genuinely streams
end-to-end (upstream call → translation → client) on every code path, but two
things outside the router's own generator logic can silently defeat that if
not handled:

- **`X-Accel-Buffering: no`** is set on every SSE `StreamingResponse`. Without
  it, an nginx-based reverse proxy or ingress with default buffering would
  hold the entire response until it completes before forwarding any of it —
  the router's own code streams correctly, but the proxy in front of it
  wouldn't.
- **`FastApiLoggingMiddleware`** (applied gateway-wide, not router-specific)
  used to fully drain a `StreamingResponse`'s body iterator into memory
  whenever DEBUG logging was enabled for `HTTP_TRACING_LOG_LEVEL` — exactly
  the failure mode above, caused by application middleware rather than a
  proxy. It now peeks only the first chunk (which is all it ever logged) and
  re-chains the rest of the iterator lazily. `HTTP_TRACING_LOG_LEVEL=DEBUG`
  is set in this repo's `docker-compose.yml` for local dev, so this path is
  exercised on every local streaming request, not just a rare production
  configuration.

**Client disconnect handling:** the router checks `request.is_disconnected()`
on each chunk while relaying a stream (both the `api_type: openai` and
`api_type: anthropic` streaming paths) and stops pulling further chunks from
the upstream the moment the client disconnects (Ctrl-C, network drop). Without
this, a client giving up mid-generation would leave the router still
consuming — and paying for — upstream tokens nobody will receive. This only
stops *upstream consumption*; the SSE write side to an already-closed client
connection is handled independently by Starlette/the ASGI server.

### SSE content-block well-formedness (2026-07-14 incident)

**Symptom:** Claude Code's context-usage percentage stayed at 0% until
auto-compact recalculated it from scratch, and its debug log showed `Error
streaming, falling back to non-streaming mode: Content block not found`
immediately after the first chunk of a stream arrived.

**Root cause:** an Anthropic SSE stream is only valid if every
`content_block_delta`/`content_block_stop` event's index was previously
opened by a `content_block_start`, and the finished message has at least one
content block. Two independent gaps let the router emit a stream violating
that invariant:

* **`_stream_bedrock_converse_to_anthropic`** (`converse_stream_adapter.py`,
  the `MODEL_ROUTING_BEDROCK_TRANSPORT: native` path — now the default; see
  below) — AWS Bedrock's Converse API, for `qwen.qwen3-coder-next` over the
  native transport, skips `contentBlockStart` entirely and goes straight to
  `contentBlockDelta`. The translator forwarded that delta verbatim,
  producing a delta for a block index the client had never seen opened. This
  was the actual live trigger of the symptom above.
* **`_stream_oai_sdk_to_anthropic`** (`stream_converter.py`, the Mantle
  path) — the inline error-visibility guard checked `not sent_message_start`
  instead of `not open_blocks`. `sent_message_start` goes `True` as soon as
  the first upstream chunk arrives, so a failure later in the stream (e.g.
  the model exhausting `max_tokens` while still inside an unterminated
  `<think>` block, before any visible text ever surfaced) silently closed an
  empty assistant message instead of showing error text — a well-formed but
  misleading stream, found while auditing the Mantle path for the same class
  of bug.

Diagnosing which of the two translators was actually live took longer than
fixing it: the router logs `-> BEDROCK ... api=openai streaming=True`
regardless of which transport handles the request, so that line alone doesn't
tell you whether `_bedrock_transport == "native"` diverted it to
`BedrockNativeDispatcher` before ever reaching the Mantle/OpenAI SDK code.
Confirming the live path required replaying the exact captured request body
against the running gateway with `curl` and instrumenting each candidate
translator directly, rather than trusting that log line.

**Fix:** both translators now (a) lazily open a content block on its first
delta if the upstream never sent an explicit start event, and (b) emit at
least one empty content block if a completion ends with none opened and no
error (e.g. the model exhausts its token budget entirely inside hidden
reasoning). The error-visibility guards in both translators are gated on
"has any block ever opened" rather than "has message_start been sent" or
"are any blocks currently open" — either of the latter two can be true/false
at the wrong time and either miss a real error or collide with an
already-open block.

Audited and confirmed safe by construction, no fix needed: Anthropic
passthrough streaming and non-streaming (byte-for-byte relay, no
transformation), non-streaming Mantle/Converse responses (a JSON body's
`content` array has no SSE index-matching invariant to violate, even if
empty), and `router.py`'s `_error_response` (already always opens a block
before its first delta). Regression tests: `test_stream_converter.py` and
`test_converse_stream_adapter.py`.

**Follow-up (same day):** a genuine Bedrock Mantle backend failure in a
deployed environment — a bare `internal_server_error` 500 six minutes into a
stream — prompted two further changes, since diagnosing *that* incident
required inferring from error shape alone that Mantle (not native) had
handled the request:

- `MODEL_ROUTING_BEDROCK_TRANSPORT` now defaults to `"native"` instead of
  `"mantle"` — `"mantle"` is the manual opt-out instead of the default. See
  `LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport`
  and the updated `docs/superpowers/specs/2026-07-13-native-bedrock-transport-design.md`.
- Every `model-router-usage`/`model-router-errors` record now carries a
  `bedrock_transport` field (`"native"`/`"mantle"`) whenever
  `backend == "aws_bedrock"` — see the field references below — so which
  transport handled a given request is a direct field, not an inference from
  `error_message` shape or response headers.

---

## Usage tracking

### Purpose

`UsageTracker` (`language_model_gateway/gateway/routers/model_routing/usage_tracker.py`)
writes one document per request to a MongoDB collection
(`MODEL_ROUTING_USAGE_COLLECTION_NAME`, default `model-router-usage`) whenever
`MONGO_LLM_STORAGE_URI` is set. It exists to answer, after the fact: who made
this request (best-effort), which model/tier/backend served it, how many
tokens it used, what it cost vs. what it would have cost at Anthropic's own
price, and whether it streamed. There is no read path in this codebase for
this collection — it's written for downstream reporting/BI, not consumed by
the router itself.

**Coverage:** both `api_type: openai` routes (Bedrock Mantle) and
`api_type: anthropic` routes (direct-to-Anthropic passthrough and
Bedrock-native-Anthropic-format) record usage, for both streaming and
non-streaming requests.

- `api_type: openai` requests are translated to/from OpenAI's wire format
  anyway, so usage falls out of that translation (`stream_converter.py`'s
  `_stream_oai_sdk_to_anthropic`/`_oai_stream_with_usage_tracking`, or a
  parsed `resp.model_dump()` for non-streaming).
- `api_type: anthropic` requests need no translation (the upstream already
  speaks Anthropic's wire format), so usage is captured differently:
  non-streaming responses are buffered and parsed as JSON (same amount of
  buffering the `>=400` error branch already did); streaming responses are
  relayed **byte-for-byte, unmodified** while a lightweight sniffer
  (`_parse_anthropic_sse_usage` in `stream_converter.py`) reads the same
  bytes for `message_start`/`message_delta`/`content_block_delta` events —
  it never re-encodes or alters what the client receives.

### How a record gets written

`record_usage()` is the single place that assembles and inserts the document;
`record_usage_from_openai_response()`/`record_usage_from_anthropic_response()`
are thin wrappers that pull tokens/response text out of the upstream response
shape and call it. A record is only written when `input_tokens +
output_tokens > 0` — a request with zero usage on both sides is silently
skipped.

**Never blocks the response** — the MongoDB write always happens after the
response has already been sent to the client, so a slow or failing write
never adds latency or errors to the proxy call itself. Write failures are
caught and logged, never raised.
- Non-streaming: scheduled via Starlette `BackgroundTasks`, which Starlette
  runs only after the response body has been fully sent.
- Streaming: fire-and-forget via `asyncio.create_task()` from the stream
  generator's `finally` block (see `_fire_and_forget` in
  `stream_converter.py`), so the SSE stream can close as soon as the last
  chunk is sent instead of waiting on the write.

### Field reference

Every record always has `request_id`, `model`, `input_tokens`,
`output_tokens`, `total_tokens`, `timestamp` (UTC). Everything else is
written only when the corresponding value is available for that request —
absence of a field means "not available for this request," not an error.

| Field | Type | Always present? | Meaning |
|-------|------|------------------|---------|
| `request_id` | string | always | Anthropic-format message id (`msg_...`) generated per request. |
| `model` | string | always | The **upstream** model id actually called (e.g. `qwen.qwen3-coder-next`), not the client-requested `claude_model`. |
| `input_tokens` / `output_tokens` / `total_tokens` | int | always | From the upstream response's own usage block. |
| `timestamp` | datetime (UTC) | always | Set at write time, i.e. after the response was already sent — not the time the request arrived. Kept for backward compatibility; equal to `end_time`. |
| `start_time` | datetime (UTC) | always | Captured at the very top of `proxy_messages`, before body parsing or any upstream call — the client's request-arrival time. |
| `end_time` | datetime (UTC) | always | When this record was written — for streaming requests, that's after the stream has fully drained (the wrapper's `finally` block), so it's effectively "response fully delivered," not just upstream's first byte. |
| `duration_ms` | float | always | `end_time - start_time` in milliseconds. Includes the entire upstream generation time for streaming requests — this is "how long the client waited," not the proxy's own overhead (see `upstream_latency_ms` on the OTel span for that). |
| `user_id` | string | when attribution succeeds | See "Attribution" below. |
| `auth_provider` | string | when `user_id` is set | **Provenance of `user_id`, not a fixed enum of identity providers.** Either the real IdP name from a verified OIDC token (e.g. `"okta"`), or the literal string `"custom-header"` meaning `user_id` came from the self-asserted `{prefix}user-id` header — unverified, spoofable by anyone who can reach this router. Check this field before trusting `user_id` for anything security-sensitive. |
| `email` / `user_name` | string | when OIDC verification succeeds | Only populated on the verified-identity path — never set via the custom-header fallback. |
| `session_id` | string | when Claude Code sends it | Correlates requests within one CLI session. Read from the documented `x-claude-code-session-id` header (see [gateway protocol reference](https://code.claude.com/docs/en/llm-gateway-protocol)) when present; falls back to parsing Claude Code's `body.metadata.user_id` JSON blob (`{device_id, account_uuid, session_id}`) otherwise. Client-supplied and unverified, but not an identity field, so it's trusted for correlation purposes regardless of auth state. |
| `account_uuid` | string | when Claude Code sends it | From the same `body.metadata.user_id` JSON blob as the `session_id` fallback. Opaque per-Anthropic-account identifier; stored raw — this router does **not** resolve it to an email at request time (see "Account directory" below). |
| `agent_id` / `parent_agent_id` | string | only on requests from a subagent Claude Code spawned | From the `x-claude-code-agent-id`/`x-claude-code-parent-agent-id` headers. Identifies an agent, not a person or device — use alongside `session_id` to attribute cost to parallel subagents, never as a user identifier. |
| `model_tier` | string | when the route matched a config entry | The `tier` label from `model-router-config.json` (e.g. `"sonnet"`). Absent for unmatched-model fallback requests. |
| `backend` | string | when the route matched | `"anthropic"` (passthrough) or `"aws_bedrock"` (aws auth), derived from the route's `auth` field. |
| `bedrock_transport` | string | when `backend == "aws_bedrock"` | `"native"` or `"mantle"` — which Bedrock transport actually handled this request. `auth`/`api_type` alone can't tell them apart, since native Converse dispatch is also reached via `auth="aws"`, `api_type="openai"` routes; see "SSE content-block well-formedness" above for why this field exists. |
| `price_per_mtok` → `cost_usd` | float (USD) | when the route has `price_per_mtok` configured | `cost_usd = total_tokens / 1_000_000 * price_per_mtok` — the actual cost at the backend that served this request. |
| `anthropic_price_per_mtok` → `anthropic_cost_usd` | float (USD) | when the route also has `anthropic_price_per_mtok` configured | `anthropic_cost_usd = total_tokens / 1_000_000 * anthropic_price_per_mtok` — what the client's requested `claude_model` would have cost at Anthropic's own list price. For passthrough routes (opus/fable) this equals `cost_usd`, since the backend *is* Anthropic. |
| `cost_savings_usd` | float (USD) | alongside `anthropic_cost_usd` | `anthropic_cost_usd - cost_usd`. Zero for passthrough routes; positive for Bedrock routes serving a cheaper model in place of the requested Claude tier. |
| `streaming` | bool | always, once any request reaches the recording point | Whether the client's original request had `"stream": true`. |
| `compression_requested` | string | when the client sent one | Raw `Accept-Encoding` request header (e.g. `"gzip, deflate, br, zstd"`) — what the client said it could accept. |
| `compression_used` | string | always alongside `compression_requested`'s recording point | `"gzip"` or `"none"` — what the gateway's `GZipMiddleware` actually did. Streaming responses are always `"none"`: Starlette hardcodes `text/event-stream` into `GZipMiddleware`'s excluded content types regardless of `Accept-Encoding` (see `api.py`). For non-streaming responses it's computed by replicating Starlette's own decision (gzip if the client accepts it and the body is ≥500 bytes) before the middleware runs, since the usage record is written from a background task after the middleware has already acted. |
| `custom_headers` | object (flat string→string map) | when any header under `MODEL_ROUTING_CUSTOM_HEADER_PREFIX` is present | **Every** header under the configured prefix, keyed by the suffix after the prefix — e.g. `X-Model-Routing-Client-Type: claude code` becomes `{"client-type": "claude code"}`. Deliberately open-ended: new attribution headers can be added by any client without a code change here. `{prefix}user-id` is additionally pulled out into the top-level `user_id` field (see "Attribution"). |
| `input_preview` / `output_preview` | string | only when `MODEL_ROUTING_USAGE_CAPTURE_PREVIEWS=true` | First `MODEL_ROUTING_USAGE_PREVIEW_CHARS` characters of the last user message / model response text, truncated with a trailing `…` marker when the original was longer (so `"…"` present tells you the preview is a prefix, not the whole thing). Off by default — this is the one field group that persists actual conversation content rather than metadata. |
| `sse_event_count` | int | streaming (`api_type: openai`) requests only | Number of SSE events actually yielded to the client for this response. A cheap sanity signal that the response really streamed rather than being buffered and dumped as one blob — a long generation with a suspiciously low count (e.g. 1) is worth investigating. Not recorded for non-streaming requests, nor for `api_type: anthropic` streaming — that path relays bytes verbatim rather than yielding discrete translated events, so there's nothing analogous to count. |

### Session rollup

Alongside the per-request document, `record_usage()` upserts a second document
per `session_id` into `MODEL_ROUTING_USAGE_SESSION_COLLECTION_NAME` (default
`model-router-sessions`) — one row per session instead of one per request, so
session-level totals don't need a `$group` aggregation over the larger
per-request collection. Requests without a `session_id` don't produce a
session document at all (there's nothing to key it on).

This is a rollup, not a replacement — the per-request collection remains the
source of truth for per-request detail (previews, compression, streaming
flag, timing). The session document only carries fields that are meaningful
as a running total.

Cost is bucketed by tier rather than by exact model, because a single session
can span multiple model tiers and there's no per-model array on this
document — an unbounded array would risk hitting MongoDB's 16MB document
limit on a long-running agent session:

| `model_tier` | Bucket |
|--------------|--------|
| `haiku` | `low` |
| `sonnet` | `medium` |
| `opus` | `high` |
| `fable` | `fable` |

Fields: `session_id`, `account_uuid`, `user_id`, `input_tokens`,
`output_tokens`, `total_tokens`, `{bucket}_tier_cost`,
`{bucket}_tier_anthropic_cost`, `{bucket}_tier_model` (one triple per bucket
actually used by the session), and `total_savings_usd` (session-wide sum of
`anthropic_cost_usd - cost_usd` across every request, regardless of tier).

Token and cost fields use MongoDB's `$inc` so concurrent requests within the
same session (e.g. parallel subagent calls sharing one `session_id`)
accumulate correctly instead of racing on a last-write-wins `$set`.
`account_uuid`/`user_id`/`{bucket}_tier_model` are plain `$set` since they're
stable per session in practice. A failure writing the session rollup is
logged and swallowed — it never affects the per-request write that already
succeeded, and it never surfaces to the client.

`MODEL_ROUTING_USAGE_SESSION_TRACKING_ENABLED` (default `true`) toggles the
session rollup independently of per-request tracking.

### Attribution

The client's `Authorization` header on this router is the upstream
Anthropic/Bedrock credential, not necessarily a b.well-issued OIDC token, so
it can't gate the proxy call itself. `user_id` is populated by the first of
these that applies, in order:

1. **OIDC-verified token.** If `Authorization` verifies as a genuine,
   signature-checked JWT via the configured `TokenReader`, `user_id`/`email`/
   `user_name` come from the token's claims, and `auth_provider` is set from
   the `x-auth-provider` header. This is the only path that also sets `email`
   and `user_name`.
2. **Custom-header fallback.** If there's no verified identity,
   `{MODEL_ROUTING_CUSTOM_HEADER_PREFIX}user-id` (e.g. Claude Code's
   `ANTHROPIC_CUSTOM_HEADERS` set to `X-Model-Routing-User-Id: ...`) is used
   as-is for `user_id`, with `auth_provider` set to the literal string
   `"custom-header"`. This is exactly as spoofable as any other
   caller-controlled header — it's accepted because this router is deployed
   per-user/local rather than as a shared multi-tenant ingress. **Do not**
   enable this fallback's trust model on a shared deployment without
   re-gating it behind verification.
3. **No match.** `user_id` is omitted entirely. Caller-supplied identity
   headers outside the configured custom-header prefix (e.g.
   `x-openwebui-user-id`) are never trusted for attribution — they're
   trivially spoofable by the caller (IDOR).

### Account directory (manual, not live)

Claude Code sends an opaque `account_uuid` on every request (see
`account_uuid` in the field reference above), but Anthropic exposes no API to
resolve it to a human email. `AccountDirectory`
(`account_directory.py`) exists to hold a **manually-imported**
`{_id: account_uuid, email}` lookup table in
`MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` (populated from an
Anthropic/Claude Console admin export — there is no import tooling in this
repo; load it directly with `mongoimport`/Compass) — but this router does
**not** query it live on the request path. `account_uuid` is stored raw on
the usage record, and the `account_uuid` → email join happens downstream in
reporting, against whatever's currently in that collection. This means a
usage record's resolved identity can change over time as the directory is
updated, without needing to reprocess old records.

---

## Error tracking

`ErrorTracker` (`language_model_gateway/gateway/routers/model_routing/error_tracker.py`)
is `UsageTracker`'s sibling for failures: one document per failed upstream
request in `MODEL_ROUTING_ERROR_COLLECTION_NAME` (default
`model-router-errors`), whenever `MONGO_LLM_STORAGE_URI` is set. Same
lazy-connect, fire-and-forget, never-raise posture as usage tracking — a
failure to write an error record is logged and swallowed, never surfaced to
the client, and never delays or replaces the actual error response.

Recorded failure points in `proxy_messages`:

- AWS credential/session expiry when signing a Bedrock request
  (`error_type: "bedrock_session_expired"`).
- A Bedrock Mantle (`api_type: openai`) upstream 4xx/5xx after throttle
  retries are exhausted (`error_type: "bedrock_upstream_error"`,
  `status_code` set).
- A Bedrock Mantle stream that fails after it had already started emitting
  chunks (`error_type: "bedrock_stream_error"`) — e.g. the bare,
  undiagnosable `internal_server_error` 500s that motivated the native
  transport (see "SSE content-block well-formedness" above and
  `docs/superpowers/specs/2026-07-13-native-bedrock-transport-design.md`).
- The native Bedrock Converse path's equivalent failures, non-streaming and
  mid-stream alike (`error_type: "bedrock_native_error"`).
- Any other unexpected exception from the Bedrock Mantle path
  (`error_type` set to the exception's class name), recorded just before
  it's re-raised.
- An `api_type: anthropic` upstream response with `status_code >= 400`
  (`error_type: "upstream_error"`, `status_code` set).

Fields: `request_id`, `model`, `error_type`, `error_message` (truncated to
1000 chars — for triage/trend-spotting, not full incident replay),
`timestamp`, `start_time`/`end_time`/`duration_ms` (same meaning as on usage
records), plus whatever attribution/context is available at the failure
point (`user_id`, `session_id`, `account_uuid`, `agent_id`,
`parent_agent_id`, `model_tier`, `backend`, `bedrock_transport`, `auth`,
`api_type`, `streaming`, `status_code`) — each omitted rather than null when
not available, same convention as the usage collection. `bedrock_transport`
("native"/"mantle") is filled in automatically from
`CodingModelRouter._bedrock_transport` whenever `backend == "aws_bedrock"` —
callers don't pass it themselves, since `auth`/`api_type` alone can't tell
a Mantle error apart from a native Converse one.

---

## Integration with the gateway

`CodingModelRouter` is registered in `language_model_gateway/gateway/api.py`
at startup with the default prefix `/v1`:

```python
app1.include_router(CodingModelRouter().get_router())
```

No authentication middleware is applied to this router at the FastAPI layer.
Auth is handled implicitly: `passthrough` routes relay the client's
`Authorization` header to Anthropic, and `aws` routes use SigV4 signing.

---

## Configuring a client to use the router

Set `ANTHROPIC_BASE_URL` to point at the gateway host.  For `passthrough`
routes (opus/fable), Claude Code's own `Authorization` header is forwarded
verbatim to Anthropic — no separate `ANTHROPIC_API_KEY` env var is required
at the gateway level.

**Anthropic SDK (Python)**

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:5050",   # gateway host (docker-compose port)
    api_key="dummy",                    # required by the SDK; not forwarded for aws routes
)
```

**Claude Code — one-off**

| Environment | Base URL |
|-------------|----------|
| Local (`make up`) | `http://localhost:5050` |
| Production | `https://language-model-gateway.services.bwell.zone` |

```sh
# local
export ANTHROPIC_BASE_URL=http://localhost:5050
claude

# production
export ANTHROPIC_BASE_URL=https://language-model-gateway.services.bwell.zone
claude
```

**Claude Code — shell function (`~/.zshrc`)**

Add the following block to your `~/.zshrc` to get a `claude-router` command
that enables routing for a single invocation without affecting plain `claude`:

```zsh
# >>> claude model routing >>>
# Run Claude Code WITH local model routing (Mode A — OAuth subscription).
# Plain 'claude' is unaffected and still talks to Anthropic directly.
# Session model is 'opusplan': Opus for plan-mode (complex reasoning), Sonnet for
# execution (normal coding); Haiku still handles background tasks. Override per run
# with 'claude-router --model sonnet' or /model.
claude-router() {
  # For production swap the URL below:
  # ANTHROPIC_BASE_URL="https://language-model-gateway.services.bwell.zone"
  echo "[model-router] proxy=localhost:5050" >&2
  env -u ANTHROPIC_API_KEY \
    ANTHROPIC_BASE_URL="http://localhost:5050" \
    ANTHROPIC_MODEL="opusplan" \
    CLAUDE_CODE_MAX_OUTPUT_TOKENS="200000" \
    CLAUDE_CODE_AUTO_COMPACT_WINDOW="262144" \
    CLAUDE_AUTOCOMPACT_PCT_OVERRIDE="80" \
    DISABLE_NON_ESSENTIAL_MODEL_CALLS="1" \
    CLAUDE_CODE_ATTRIBUTION_HEADER="0" \
    DISABLE_AUTOUPDATER="1" \
    DISABLE_TELEMETRY="1" \
    DISABLE_ERROR_REPORTING="1" \
    claude \
      "$@"
}
# <<< claude model routing <<<
```

Key env vars:

| Variable                            | Purpose                                                                                                                         |
|-------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| `-u ANTHROPIC_API_KEY`              | Unsets any existing key so it is not accidentally forwarded to `aws` routes                                                     |
| `ANTHROPIC_BASE_URL`                | Points Claude Code at the gateway instead of `api.anthropic.com`                                                               |
| `ANTHROPIC_MODEL`                   | Sets the default session model (`opusplan` = Opus for plan mode, Sonnet for execution)                                          |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS`     | Upper bound Claude Code requests for output; the gateway caps this server-side to `reserved_output_tokens` (32 768)             |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW`   | Tells Claude Code the total context window size (262 144 = Qwen's actual limit)                                                 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`   | Compact conversation history at this % of the window. 80 % × 262 144 ≈ 210 k tokens, leaving ~15 k margin before the 225 k effective input budget |
| `CLAUDE_CODE_ATTRIBUTION_HEADER`    | Prevents a per-request header from changing between calls, which would otherwise invalidate any server-side KV cache            |
| `DISABLE_NON_ESSENTIAL_MODEL_CALLS` | Suppresses background Claude calls (auto-title etc.) that would bypass the router directly                                      |

The client sends requests to `/v1/messages` exactly as it would to
`api.anthropic.com`.  The router rewrites the destination based on the config
file without any change to the client-side request format.
