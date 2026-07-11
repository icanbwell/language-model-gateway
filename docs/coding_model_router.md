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
      "price_per_mtok": 0.5,                  // cost per million tokens (informational, not enforced)

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
