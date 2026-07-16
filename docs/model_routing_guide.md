# Model Routing Guide

> **Note:** [`coding_model_router.md`](coding_model_router.md) is the
> canonical, actively-maintained reference for `CodingModelRouter` —
> route config schema, env vars, transport options, etc. This guide
> overlaps with it substantially and has already drifted in places (e.g.
> the route JSON below is missing fields like `anthropic_price_per_mtok`
> and `tokenizer_model` that the real config carries). Prefer the other
> doc; this one is kept for its local dev / shell-wrapper walkthrough
> until that's folded in or this file is retired.

This guide explains how to configure model routing for the language model gateway.

## Overview

The language model gateway is a proxy that routes Anthropic Messages API requests to different backends (Anthropic direct or AWS Bedrock) based on a JSON configuration file. Clients send requests to the gateway's `/v1/messages` endpoint exactly as they would to `api.anthropic.com`, and the router forwards them to the appropriate upstream based on the `model` field in the request.

## Configuration

The router configuration is loaded from `model-router-config.json` (configurable via `ROUTER_CONFIG` environment variable).

### Route Configuration Schema

Each route in the config has these key fields:

| Field | Description |
|-------|-------------|
| `tier` | Route tier name (haiku, sonnet, opus, fable) |
| `claude_model` | Exact model name for fastest lookup |
| `claude_model_pattern` | Optional regex pattern for fallback matching |
| `url` | Upstream API endpoint |
| `model` | Backend model name (Bedrock or Anthropic) |
| `auth` | Authentication type (`passthrough` or `aws`) |
| `aws_region` | AWS region for Bedrock routes |
| `api_type` | Wire protocol (`anthropic` or `openai`) |
| `context_window` | Total context window size |
| `max_tokens` | Reserved output tokens |
| `price_per_mtok` | Cost per million tokens |

### Current Production Routes

```json
{
  "routes": [
    {
      "tier": "haiku",
      "claude_model": "claude-haiku-4-5-20251001",
      "claude_model_pattern": "^claude-haiku-",
      "url": "https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions",
      "model": "qwen.qwen3-coder-30b-a3b-v1:0",
      "auth": "aws",
      "aws_region": "us-east-1",
      "api_type": "openai",
      "price_per_mtok": 0.15,
      "context_window": 262144,
      "max_tokens": 32768
    },
    {
      "tier": "sonnet",
      "claude_model": "claude-sonnet-5",
      "claude_model_pattern": "^claude-sonnet(-|$)",
      "url": "https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions",
      "model": "qwen.qwen3-coder-next",
      "auth": "aws",
      "aws_region": "us-east-1",
      "api_type": "openai",
      "price_per_mtok": 0.5,
      "context_window": 262144,
      "max_tokens": 32768
    },
    {
      "tier": "opus",
      "claude_model": "claude-opus-4-8",
      "claude_model_pattern": "^claude-opus-",
      "url": "https://api.anthropic.com/v1/messages",
      "model": "claude-opus-4-8",
      "auth": "passthrough"
    },
    {
      "tier": "fable",
      "claude_model": "claude-fable-5",
      "claude_model_pattern": "^claude-fable-",
      "url": "https://api.anthropic.com/v1/messages",
      "model": "claude-fable-5",
      "auth": "passthrough"
    }
  ]
}
```

## Shell Configuration (Claude Router)

Add the following to your `~/.zshrc`:

```bash
# >>> claude model routing >>>
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
alias install-model-router="bash $HOME/model-router/install-model-router.sh"
alias uninstall-model-router="bash $HOME/model-router/uninstall-model-router.sh"
alias start-model-router="bash $HOME/model-router/start-model-router.sh"
alias stop-model-router="bash $HOME/model-router/stop-model-router.sh"
# <<< claude model routing <<<
```

### Environment Variables Explained

| Variable | Purpose |
|----------|---------|
| `-u ANTHROPIC_API_KEY` | Unsets any existing key (not forwarded to AWS routes) |
| `ANTHROPIC_BASE_URL` | Points Claude Code at the gateway instead of `api.anthropic.com` |
| `ANTHROPIC_MODEL` | Default session model (`opusplan` = Opus for plan mode, Sonnet for execution) |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Upper bound for Claude Code output requests (gateway caps server-side to `max_tokens`) |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Total context window size for auto-compaction |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Compact conversation history at this % of window (80% × 262144 ≈ 210k tokens) |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` | Prevents header changes between calls (enables server-side KV cache) |
| `DISABLE_NON_ESSENTIAL_MODEL_CALLS` | Suppresses background Claude calls that bypass the router |
| `DISABLE_AUTOUPDATER`, `DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING` | Keep routed session from phoning home |

## How Routing Works

1. Client sends request to `/v1/messages` with `model` field (e.g., `"claude-sonnet-5"`)
2. Router looks up `model` in exact-match route dict (fast path)
3. If no exact match, tries each `claude_model_pattern` regex in order
4. Forwards to configured upstream with appropriate auth handling:
   - `passthrough`: Forwards `Authorization` header as-is (Anthropic API)
   - `aws`: Signs request with SigV4 (AWS Bedrock)
5. Translates response format if needed (`openai` → `anthropic`)

## Model Fallback Behavior

- **Exact match first**: Routes with `claude_model` matching the request model
- **Pattern fallback**: Routes with matching `claude_model_pattern` regex (e.g., `^claude-haiku-` matches `claude-haiku-4-5-20251001`)
- **Unknown models**: Falls back to Anthropic direct if no route matches

## Statusline: Session Savings

This gateway exposes `GET /v1/model-routing/sessions/{session_id}/savings`,
returning the current Claude Code session's cumulative cost savings (vs.
Anthropic list price) from being routed through this gateway, broken down by
model tier. `scripts/claude_code_statusline.py` turns that into a Claude Code
statusline message.

1. Set `MODEL_ROUTING_GATEWAY_URL` in your shell profile to this gateway's
   base URL (the same host Claude Code's `ANTHROPIC_BASE_URL` already points
   at).
2. Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /absolute/path/to/scripts/claude_code_statusline.py"
  }
}
```

The footer shows nothing until the session has at least one completed
request — this is expected, not an error. If the gateway is unreachable or
slow, the script fails silent within ~2 seconds rather than stalling Claude
Code's UI.

## Key Points

- The router is **wire-compatible** - clients send exactly the same format as they would to `api.anthropic.com`
- No client-side changes required - just set `ANTHROPIC_BASE_URL` to point at the gateway
- Route config is loaded once at module import time; restart containers or call `_reload_routes()` for changes
- Usage attribution requires either valid OIDC token or custom headers (`X-Model-Routing-User-Id`, `X-Model-Routing-Client-Type`)
