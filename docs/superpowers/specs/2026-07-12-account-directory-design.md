# Account Directory — account_uuid → email resolution for usage attribution

## Problem

Usage-tracking records written by `UsageTracker` (Mongo `usage`/`model-router-usage`
collection) are meant to be attributable to a real human, but for the actual traffic this
router serves — Claude Code sessions authenticated with a personal Anthropic subscription
OAuth token — the existing OIDC-verification path in `_get_auth_info` never populates
`user_id`/`email`:

- The `Authorization` header on every Claude Code request is the client's own Anthropic
  subscription OAuth token (`sk-ant-oat01-...`), confirmed by inspecting real local traffic
  with `DEBUG_LOG_RECEIVED_OAUTH_TOKENS`. It is never a b.well-issued OIDC JWT, so
  `TokenReader.verify_token_async()` always fails to verify it and `auth_info["user_id"]`
  stays unset for this traffic pattern.
- Claude Code has no supported mechanism (env var, `settings.json` key, or CLI flag) to
  inject custom HTTP headers carrying a real identity — confirmed via Claude Code
  documentation research.
- Every request body does carry `metadata.user_id`, a JSON string
  (`{"device_id": ..., "account_uuid": ..., "session_id": ...}`) that Claude Code sends
  automatically as part of the standard Anthropic SDK request shape. `account_uuid` is
  stable per Anthropic account but is an opaque internal identifier — there is no supported
  Anthropic API to resolve it to a human-readable name or email.
- The Anthropic/Claude Console admin export *does* include `account_uuid` alongside each
  member's email (confirmed by the user), making a manually-populated lookup table a
  practical way to bridge the two.

## Goal

Resolve `account_uuid` → email using a small, manually-populated Mongo lookup table, and
use that resolved email to enrich usage-tracking records when the OIDC-verified path
doesn't already provide one.

## Non-goals (this pass)

- Injecting the resolved identity into the outbound Bedrock Mantle request as OpenAI's
  `user` field — deferred as a separate follow-up.
- Building an import script/CLI for loading the export — the user will populate the
  collection directly via `mongoimport`/Compass against the schema documented below.
- Any self-service registration flow (e.g. an endpoint engineers call to register their own
  `account_uuid`) — out of scope; the Console export is the source of truth.

## Design

### New class: `AccountDirectory`

New file: `language_model_gateway/gateway/routers/model_routing/account_directory.py`

```python
class AccountDirectory:
    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "account_directory",
        enabled: bool = True,
    ) -> None: ...

    async def resolve_email(self, account_uuid: str) -> str | None: ...
```

- Mirrors `UsageTracker`'s existing pattern exactly: lazy `_ensure_connected()` on first
  use, disables itself (`self._enabled = False`) and logs a warning on any Mongo connection
  failure, never raises. `resolve_email` similarly catches all exceptions from the lookup
  itself and returns `None` rather than propagating — a directory-lookup failure must never
  break the proxy call.
- `resolve_email(account_uuid)` performs `find_one({"_id": account_uuid})` and returns
  `doc.get("email")` if found, else `None`. `_id` is the natural key since `account_uuid`
  is already globally unique per Anthropic account.
- Document shape for the manually-imported collection:
  ```json
  {"_id": "<account_uuid>", "email": "<email>", "name": "<optional display name>"}
  ```
  The user maps the Console export's `account_uuid` column to `_id` when importing (e.g.
  via `mongoimport --mode upsert`).

### Wiring into `CodingModelRouter.proxy_messages`

- Near the top of `proxy_messages`, alongside the existing `auth_info` computation, parse
  `body_json.get("metadata", {}).get("user_id")` — a JSON-encoded string — and extract
  `account_uuid`. Wrapped in a broad `try/except` that swallows any parse error and leaves
  `account_uuid` as `None`: this is untrusted, client-supplied JSON and malformed input must
  never break the proxy call.
- If `account_uuid` is present, call `self._account_directory.resolve_email(account_uuid)`.
- If resolved, and `auth_info` does not already have a `user_id` set from the OIDC-verified
  path, set **both** `auth_info["user_id"]` and `auth_info["email"]` to the resolved email
  (there is no separate "subject" concept for a directory lookup — the email is the
  identity). Verified OIDC identity always wins when already present; the directory lookup
  only fills in when it isn't.
- No new call sites needed in `stream_converter.py` / the usage-tracking write paths —
  they already consume `auth_info`, so enriching it once upstream is sufficient.

### Configuration

Follows the `MODEL_ROUTING_USAGE_COLLECTION_NAME` pattern established earlier on this
branch:

- `CodingModelRouter.__init__` gains `account_directory_collection_name: str =
  "account_directory"`.
- `AccountDirectory` reuses the *same* `mongo_uri`/db as `UsageTracker` — no new connection
  string, just a second collection in the same database. `CodingModelRouter` constructs an
  `AccountDirectory` alongside `UsageTracker` under the same `if mongo_uri:` guard.
- New property `model_routing_account_directory_collection_name` on
  `LanguageModelGatewayEnvironmentVariables`, reading
  `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` (default
  `"model-router-account-directory"` — following the same class-default-vs-app-default
  split already established for `model_routing_usage_collection_name`: the constructor's
  own generic default stays `"account_directory"`; the app's actual deployed default gets
  the more specific, collision-resistant name), wired through `api.py` the same way
  `model_routing_usage_collection_name` already is.
- Helm: add `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` to
  `helm.helix-service/.helm/language-model-gateway/services.values.yaml` alongside the
  sibling collection-name entries, following the same "explicit for discoverability, not a
  behavior change" reasoning used for the usage-collection-name var.

### Error handling

- Malformed/missing `metadata.user_id` → `account_uuid` stays `None`, no lookup attempted,
  no error surfaced.
- Mongo unavailable at startup or mid-run → `AccountDirectory` disables itself (same as
  `UsageTracker`), `resolve_email` short-circuits to `None`.
- Unknown `account_uuid` (not yet imported) → `resolve_email` returns `None`, `auth_info`
  stays as it was (no attribution, same as today).
- None of these paths can raise into `proxy_messages` — attribution is strictly
  best-effort and must never affect whether a request succeeds.

### Testing

- `tests/gateway/routers/model_routing/test_account_directory.py`, mirroring
  `test_usage_tracker.py`'s structure: constructor defaults/custom values, connection
  failure → disabled, `resolve_email` found/not-found/disabled cases.
- A `test_coding_model_router.py` case asserting a resolved email lands in the usage
  record when `metadata.user_id` is present and OIDC identity isn't (the realistic Claude
  Code case), and that OIDC-verified identity is preferred over the directory lookup when
  both are present.
