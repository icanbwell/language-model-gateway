# Session savings message in Claude Code's statusline

## Context

[OpenRouterTeam/openrouter-examples/claude-code](https://github.com/OpenRouterTeam/openrouter-examples/tree/main/claude-code)
wires Claude Code's `statusLine` setting (`~/.claude/settings.json`) to a local
script that shows OpenRouter API spend in the terminal footer. Claude Code
invokes that command on every render, feeding it a JSON payload on stdin
(`session_id`, `model`, `cwd`, and Claude Code's own `cost` object) and prints
whatever the command writes to stdout as the status line.

This gateway (`language_model_gateway/gateway/routers/model_routing/`) already
computes the equivalent number for its own routing decisions.
`usage_tracker.py`'s `_upsert_session_usage` upserts a per-session rollup
document into the `model-router-sessions` collection on every request, keyed by
`session_id`, accumulating `total_savings_usd` (Anthropic list price minus
whatever this gateway's routing — Bedrock, Qwen, etc. — actually cost) and a
`{tier}_tier_cost` / `{tier}_tier_anthropic_cost` pair per tier bucket
(`low`/`medium`/`high`/`fable`). `router.py` already captures the same
`x-claude-code-session-id` Claude Code sends on every proxied request
(`_attach_claude_code_headers`), so the session_id keying that rollup is the
same one Claude Code's statusline payload will hand back to us. Claude Code's
own built-in `cost` object in the statusline payload is priced off whatever
model id it thinks it called — it has no visibility into this gateway silently
swapping in a cheaper backend, so it cannot show this number itself.

There is currently no HTTP endpoint that reads `model-router-sessions` back out —
`usage_tracker.py` only ever writes to it. A local statusline script cannot
reach MongoDB directly either: `docker-compose.yml` only exposes `mongo` on
the compose network, not to the host.

## Goals

- A new read-only gateway endpoint that returns the current session's savings
  totals, given a `session_id`.
- A statusline script + `~/.claude/settings.json` snippet that calls it and
  renders `$ saved` plus a per-tier breakdown in Claude Code's footer.
- No new auth scheme, and no weakening of the existing tenant-isolation
  posture on any *other* endpoint.

## Non-goals

- Historical/cross-session reporting or a dashboard — this is a single
  session's live rollup only.
- Any change to what `usage_tracker.py` records or how sessions are bucketed
  by tier.
- Fixing the pre-existing spoofable `user_id` custom-header fallback in
  `router.py` (see "Related fix" below) — flagged, not fixed, here.

## Architecture

### Reader: `session_savings_reader.py`

A new, read-only class in `model_routing/`, deliberately separate from
`UsageTracker` — a consumer that only needs to read a session's savings
should not depend on an interface that also exposes `insert_one`/upsert
methods (Interface Segregation). It owns its own lazy-connected
`AsyncMongoClient`, mirroring `UsageTracker._ensure_connected`'s pattern
(connect on first use, disable itself on connection failure rather than
raising into the request path), configured with the same
`mongo_uri` / `usage_db_name` / `usage_session_collection_name` already
threaded into `CodingModelRouter` from `api.py`.

One method:

```python
async def get_session_savings(self, session_id: str) -> SessionSavings | None:
    """find_one({"session_id": session_id}) against model-router-sessions, mapped
    into a typed SessionSavings — None if the session has no rollup yet
    (e.g. its first request is still in flight, or the id is unknown)."""
```

### Response contract

Pydantic models, so the endpoint has an explicit typed shape rather than
handing back the raw Mongo document:

```python
class TierSavings(BaseModel):
    model: str | None
    cost_usd: float
    anthropic_cost_usd: float

class SessionSavingsResponse(BaseModel):
    session_id: str
    total_savings_usd: float
    total_tokens: int
    tiers: dict[str, TierSavings]  # keyed by "low" / "medium" / "high" / "fable" — only tiers present in the session
```

`tiers` omits any bucket the session never touched, rather than zero-filling
all four — a Haiku-only session's response has no `"high"` key at all.

### Router: `SessionSavingsRouter`

A new router class following the existing minimal pattern (`ModelsRouter` in
`models_router.py`):

```
GET /v1/model-routing/sessions/{session_id}/savings
  -> 200 SessionSavingsResponse
  -> 404 {"error": "no usage recorded for this session"}  if get_session_savings returns None
```

Constructed with the same `mongo_uri`/`usage_db_name`/
`usage_session_collection_name` config already passed to `CodingModelRouter`,
and mounted in `api.py` alongside the other `include_router(...)` calls.

### Security posture: session_id as capability, not a new auth scheme

This endpoint has **no OAuth/OIDC gate**. Knowing the session's UUIDv4 is the
only requirement to read its savings total. This is a deliberate call, not an
oversight, for three reasons:

1. Claude Code's own `Authorization` header on this gateway is the
   developer's Anthropic subscription token, not a b.well OIDC token this
   gateway's `TokenReader` can verify (see `router.py`'s `_get_auth_info`
   docstring) — real OIDC gating would require the statusline script to
   source a *separate* credential Claude Code never gives it, turning a
   footer message into a login flow.
2. `session_id` is a random UUIDv4 that only the legitimate Claude Code
   process (and whatever it hands the id to, i.e. its own statusline command)
   ever sees — the same trust model already used for the existing
   `x-claude-code-session-id` and custom-header attribution paths elsewhere
   in this router.
3. The blast radius of a leaked session_id is a single dollar figure and a
   per-tier cost breakdown — no prompts, no responses, no PHI, no email, no
   account identity.

This is being written up explicitly (this doc) rather than left as a silent
gap, per CLAUDE.md's requirement that deviations from the OAuth/OIDC-only
baseline be a documented, reasoned decision rather than an implicit one. If
EA review disagrees with treating this as "not an auth flow" rather than "a
custom auth scheme," this needs a Tech Design Review before shipping.

### Related fix (already applied, not part of this feature)

While confirming the deployment model for this design, it came out that this
router is a **shared multi-tenant** ingress — contradicting a docstring in
`router.py`'s `_get_auth_info` (and the matching paragraph in
`docs/coding_model_router.md`) that justified the spoofable custom-header
`user_id` fallback as safe because the router was "deployed per-user/local."
Both docs have been corrected in place to flag this as a known gap: on a
shared deployment, that fallback currently lets any caller attribute their
usage cost to another user's `user_id`. This is a pre-existing billing/cost
attribution integrity issue, independent of the savings feature — flagged
here for a follow-up ticket, not fixed as part of this work.

## Data flow

1. Claude Code renders its footer → invokes the configured `statusLine`
   command → pipes its stdin JSON payload (including `session_id`) to it.
2. The script extracts `session_id`, calls
   `GET {gateway_url}/v1/model-routing/sessions/{session_id}/savings` via
   `urllib.request.urlopen()` with a short timeout (~1-2s).
3. `SessionSavingsRouter` → `SessionSavingsReader.get_session_savings` →
   `find_one` on `model-router-sessions` → typed response, or 404.
4. The script formats the response into a single line, e.g.:
   `💰 $0.42 saved (haiku $0.10 · sonnet $0.30 · opus $0.02)`
   and writes it to stdout.

## Error handling

- **No session doc yet** (first request still in flight, or an unrecognized
  id): 404 from the endpoint; the script prints nothing (empty statusline
  segment) rather than an error string, since this is a normal transient
  state at the start of a session, not a fault.
- **Gateway unreachable / slow**: the script's `urllib.request.urlopen()`
  call must use a short timeout so a down or slow gateway never visibly
  stalls Claude Code's UI — any urllib error (URLError, timeout) is
  swallowed the same as the 404 case.
- **Malformed/unexpected response body**: the script treats anything that
  doesn't parse as JSON with the expected fields the same as "no data" —
  fails silent, never prints a raw error blob into the footer.
- **Mongo connection failure on the reader side**: mirrors
  `UsageTracker._ensure_connected` — logs a warning and disables itself
  (`get_session_savings` returns `None`, i.e. the endpoint 404s) rather than
  raising into the request path.

## Testing

- `SessionSavingsReader` unit tests (mirroring `test_usage_tracker.py`'s
  `AsyncMock`/`MagicMock` style): session found with all four tiers, session
  found with only one tier present (bucket-omission behavior), session not
  found (`None`), Mongo connection failure (disables itself, returns `None`).
- `SessionSavingsRouter` contract test: 200 shape matches
  `SessionSavingsResponse`, 404 shape when the reader returns `None`.
- Statusline script: a scripted test (or documented manual check) covering
  the urllib-timeout and non-200/malformed-response paths print nothing rather
  than erroring or hanging.

## Deliverables

1. `language_model_gateway/gateway/routers/model_routing/session_savings_reader.py`
2. `language_model_gateway/gateway/routers/model_routing/session_savings_router.py`
   (or added to an existing small router file — implementation detail for the
   plan)
3. Wiring in `api.py`'s `create_app()` alongside the existing
   `CodingModelRouter` mount.
4. `scripts/claude-code-statusline.sh` (or `.py`) + a doc snippet for the
   `~/.claude/settings.json` `statusLine.command` wiring.
5. Tests per the Testing section above.
6. (Already done, ahead of the plan) Corrected docstrings in `router.py`'s
   `_get_auth_info` and `docs/coding_model_router.md`'s Attribution section,
   flagging the shared-multi-tenant custom-header spoofing gap.
