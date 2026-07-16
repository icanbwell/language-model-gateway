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
  # gateway_url="https://language-model-gateway.services.bwell.zone"
  local gateway_url="http://localhost:5050"
  echo "[model-router] proxy=$gateway_url" >&2
  env -u ANTHROPIC_API_KEY \
    ANTHROPIC_BASE_URL="$gateway_url" \
    MODEL_ROUTING_GATEWAY_URL="$gateway_url" \
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
setup-model-router-statusline() {
  local gateway_url="${MODEL_ROUTING_GATEWAY_URL:-http://localhost:5050}"
  local script_path="$HOME/.claude/scripts/claude_code_statusline.py"
  mkdir -p "$(dirname "$script_path")"
  if ! curl -fsSL "$gateway_url/static/claude_code_statusline.py" -o "$script_path"; then
    echo "[model-router] failed to download from $gateway_url -- is the gateway reachable?" >&2
    return 1
  fi
  chmod +x "$script_path"
  echo "[model-router] statusline script installed at $script_path" >&2
  echo "[model-router] add this to ~/.claude/settings.json:" >&2
  echo "  {\"statusLine\": {\"type\": \"command\", \"command\": \"python3 $script_path\"}}" >&2
}
# <<< claude model routing <<<
```

### Environment Variables Explained

| Variable | Purpose |
|----------|---------|
| `-u ANTHROPIC_API_KEY` | Unsets any existing key (not forwarded to AWS routes) |
| `ANTHROPIC_BASE_URL` | Points Claude Code at the gateway instead of `api.anthropic.com` |
| `MODEL_ROUTING_GATEWAY_URL` | Same gateway host, for the [statusline script](#statusline-session-savings) — set from the same `gateway_url` local var so it never drifts from `ANTHROPIC_BASE_URL` when you swap environments |
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
model tier. `claude_code_statusline.py` turns that into a Claude Code
statusline message. Nothing here is a gateway server change — it's entirely
local setup on your own machine, and it does **not** require cloning this
repo: the script is downloaded directly from the gateway itself, since it's
served as a static asset alongside the app's other static files (same
mechanism as the login/branding pages under `/static`).

### Prerequisites

- The [Shell Configuration](#shell-configuration-claude-router) above is
  already set up — it's what exports `MODEL_ROUTING_GATEWAY_URL` for you (see
  the table above), so there's nothing extra to configure for that part.
- `python3` on your `PATH` (macOS/Linux ship this by default; no extra
  packages needed — the script only uses the standard library).
- `curl` (or any way to download a URL) to fetch the script.

### Setup

1. **Download the script** from the gateway itself — no repo clone needed.
   The [Shell Configuration](#shell-configuration-claude-router) snippet
   above already includes a `setup-model-router-statusline` shell function
   that does this for you and prints the exact `settings.json` snippet to
   add (including the resolved absolute path):

   ```bash
   setup-model-router-statusline
   ```

   Or do it by hand if you'd rather see each step:

   ```bash
   mkdir -p ~/.claude/scripts
   curl -fsSL "$MODEL_ROUTING_GATEWAY_URL/static/claude_code_statusline.py" \
     -o ~/.claude/scripts/claude_code_statusline.py
   chmod +x ~/.claude/scripts/claude_code_statusline.py
   ```

   (Run this from a shell where `claude-router` has already exported
   `MODEL_ROUTING_GATEWAY_URL` — see Troubleshooting below if it's empty.
   You can also substitute the gateway's URL directly if you'd rather not
   depend on that being set yet.)

2. **Test it manually before wiring it into Claude Code.** Start a
   `claude-router` session, send at least one message so a usage record
   exists, then copy that session's ID from the transcript's
   `x-claude-code-session-id` (or just grab any `session_id` you've used
   recently) and pipe a fake statusline payload into the downloaded script
   by hand:

   ```bash
   echo '{"session_id": "<your-session-id>"}' | python3 ~/.claude/scripts/claude_code_statusline.py
   ```

   You should see a line like
   `💰 $0.12 saved (costs: Haiku(AWS) $0.03 · Sonnet(Anthropic) $0.09)`. The
   parenthetical is a per-tier *cost* breakdown (with the provider that
   served each tier), not a breakdown of the leading savings total — a tier
   used before backend tracking existed shows `(?)` instead of a provider
   name.
   Printing nothing at this step usually means `MODEL_ROUTING_GATEWAY_URL`
   isn't set in this shell — see Troubleshooting below.

3. **Add to `~/.claude/settings.json`, using an absolute path** (some shells
   don't expand `~` in this context, so resolve it first — skip this if you
   used `setup-model-router-statusline`, which already printed the exact
   snippet with the resolved path):

   ```bash
   realpath ~/.claude/scripts/claude_code_statusline.py
   ```

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "python3 /absolute/path/from/realpath/claude_code_statusline.py"
     }
   }
   ```

4. **Start a new Claude Code session** (`claude-router`) — the statusline
   command is read at session start, so an already-running session won't
   pick up a `settings.json` change.

To pick up a future update to the script, just re-run
`setup-model-router-statusline` (or the manual `curl` command) — it always
fetches whatever version is currently deployed on that gateway.

### Troubleshooting

- **Footer shows nothing:** expected until the session has at least one
  completed request — the gateway has no rollup to report yet. Also expected,
  silently, if the gateway is unreachable or slow (the script fails silent
  within ~2 seconds rather than stalling Claude Code's UI) — this is by
  design, not a bug to chase.
- **Still nothing after a completed request:** re-run the manual test in
  step 2 directly in a terminal, in the *same* shell you'd launch
  `claude-router` from — running it directly like that prints its own
  errors, unlike inside Claude Code's statusline. A common cause is
  `MODEL_ROUTING_GATEWAY_URL` not being set where the statusline script
  runs. Note that `claude-router` only sets it inside the one-shot `env
  ... claude "$@"` subprocess environment — it is never exported to your
  interactive shell, so `echo $MODEL_ROUTING_GATEWAY_URL` in that shell (or
  in a second terminal tab) will always come back empty even when
  everything is working correctly. To actually confirm it's being set,
  temporarily add `env | grep MODEL_ROUTING_GATEWAY_URL` right before the
  `claude "$@"` line inside the `claude-router` function and re-run it.
- **`curl` in step 1 fails or downloads an HTML error page instead of the
  script:** confirm `MODEL_ROUTING_GATEWAY_URL` actually points at a running
  gateway (`curl -fsSL "$MODEL_ROUTING_GATEWAY_URL/api/v1/models"` should
  return JSON, not an error) before troubleshooting the statusline script
  itself.
- **`command not found` in Claude Code's footer area:** check the
  `command` path in `settings.json` is absolute (not `~/...` — some shells
  don't expand `~` in this context) and that `python3` resolves on `PATH`
  for non-interactive shells too (`which python3` in a fresh terminal).

## Key Points

- The router is **wire-compatible** - clients send exactly the same format as they would to `api.anthropic.com`
- No client-side changes required - just set `ANTHROPIC_BASE_URL` to point at the gateway
- Route config is loaded once at module import time; restart containers or call `_reload_routes()` for changes
- Usage attribution (`user_id`/`email`/`user_name`) requires a valid, signature-verified OIDC token on `Authorization` — caller-supplied headers (e.g. `X-Model-Routing-User-Id`) are never trusted for attribution since they're trivially spoofable on this shared, multi-tenant router; see [Attribution](coding_model_router.md#attribution)
