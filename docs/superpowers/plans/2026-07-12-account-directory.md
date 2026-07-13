# Account Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve Claude Code's opaque `account_uuid` (sent in every request body's `metadata.user_id` field) to a human email via a manually-populated MongoDB lookup table, and use it to enrich usage-tracking attribution when the existing OIDC-verified identity path doesn't apply (which is always, for real Claude Code traffic — see spec background).

**Architecture:** A new `AccountDirectory` class mirrors `UsageTracker`'s existing lazy-connect/fail-safe Mongo pattern exactly, but is a separate class (separate responsibility: resolving identity, not writing usage). `CodingModelRouter` constructs one alongside `UsageTracker` under the same `mongo_uri` guard, and a new private method `_enrich_with_account_directory` fills in `auth_info["user_id"]`/`["email"]` from the resolved directory entry — but only when the OIDC-verified path left them unset.

**Tech Stack:** Python 3.12, pymongo `AsyncMongoClient` (already a runtime dependency via `usage_tracker.py`), pytest + pytest-asyncio (`asyncio_mode = "auto"`, no `@pytest.mark.asyncio` needed).

## Global Constraints

- Directory lookups must never raise into `proxy_messages` — any Mongo failure, parse failure, or missing entry must resolve to `None`/no-op, same fail-safe philosophy as `UsageTracker`.
- OIDC-verified identity (from `_get_auth_info`) always wins over the directory lookup when both are present — the directory lookup only fills in when `auth_info` has no `user_id` yet.
- `account_uuid` extraction from `body_json["metadata"]["user_id"]` must treat that value as fully untrusted, malformed-JSON-tolerant input.
- `AccountDirectory` reuses the *same* Mongo connection string as `UsageTracker` (no new env var for the URI) — only the collection name is configurable, via `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` (default `model-router-account-directory` at the app/env-var level; the class's own constructor default stays the generic `account_directory`, matching the `usage`/`model-router-usage` split already established for `UsageTracker`).
- Manually-imported document shape: `{"_id": "<account_uuid>", "email": "<email>", "name": "<optional>"}`. `_id` is the natural key.
- No import script — the user populates the collection directly via `mongoimport`/Compass. Out of scope for this plan.
- Wiring the resolved identity into the outbound Bedrock `user=` field is explicitly out of scope for this plan (separate follow-up).

---

### Task 1: `AccountDirectory` class + `extract_account_uuid` helper

**Files:**
- Create: `language_model_gateway/gateway/routers/model_routing/account_directory.py`
- Test: `tests/gateway/routers/model_routing/test_account_directory.py`

**Interfaces:**
- Produces: `extract_account_uuid(body_json: dict[str, Any]) -> str | None` (module-level function)
- Produces: `class AccountDirectory` with `__init__(self, mongo_uri: str, db_name: str = "llm_storage", collection_name: str = "account_directory", enabled: bool = True) -> None`, `async def resolve_email(self, account_uuid: str) -> str | None`, `async def close(self) -> None`

- [ ] **Step 1: Write the failing tests for `extract_account_uuid`**

Create `tests/gateway/routers/model_routing/test_account_directory.py`:

```python
"""
Tests for account_directory.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.account_directory import (
    AccountDirectory,
    extract_account_uuid,
)


class TestExtractAccountUuid:
    """Tests for extracting account_uuid from Claude Code's request metadata."""

    def test_extracts_account_uuid_from_valid_metadata(self) -> None:
        body_json = {
            "metadata": {
                "user_id": (
                    '{"device_id": "dev-1", "account_uuid": "acct-123", '
                    '"session_id": "sess-1"}'
                )
            }
        }
        assert extract_account_uuid(body_json) == "acct-123"

    def test_returns_none_when_metadata_missing(self) -> None:
        assert extract_account_uuid({}) is None

    def test_returns_none_when_metadata_not_dict(self) -> None:
        assert extract_account_uuid({"metadata": "not-a-dict"}) is None

    def test_returns_none_when_user_id_not_string(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": 123}}) is None

    def test_returns_none_when_user_id_not_valid_json(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": "not json"}}) is None

    def test_returns_none_when_parsed_json_not_dict(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": "[1, 2, 3]"}}) is None

    def test_returns_none_when_account_uuid_missing(self) -> None:
        body_json = {"metadata": {"user_id": '{"device_id": "dev-1"}'}}
        assert extract_account_uuid(body_json) is None

    def test_returns_none_when_account_uuid_not_string(self) -> None:
        body_json = {"metadata": {"user_id": '{"account_uuid": 123}'}}
        assert extract_account_uuid(body_json) is None
```

- [ ] **Step 2: Run tests to verify they fail with ImportError**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/model_routing/test_account_directory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'language_model_gateway.gateway.routers.model_routing.account_directory'`

- [ ] **Step 3: Create `account_directory.py` with `extract_account_uuid` only**

Create `language_model_gateway/gateway/routers/model_routing/account_directory.py`:

```python
"""Account directory for model routing.

Resolves Claude Code's opaque per-request account_uuid (sent in
body["metadata"]["user_id"]) to a human email via a manually populated
MongoDB lookup table. See docs/superpowers/specs/2026-07-12-account-directory-design.md
for the full background on why this exists.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_account_uuid(body_json: dict[str, Any]) -> str | None:
    """Best-effort extraction of Claude Code's account_uuid from request metadata.

    Claude Code sends body["metadata"]["user_id"] as a JSON-encoded string
    containing device_id/account_uuid/session_id — untrusted, client-supplied
    data. Any parse failure is swallowed; this must never raise.
    """
    try:
        metadata = body_json.get("metadata")
        if not isinstance(metadata, dict):
            return None
        raw_user_id = metadata.get("user_id")
        if not isinstance(raw_user_id, str):
            return None
        parsed = json.loads(raw_user_id)
        if not isinstance(parsed, dict):
            return None
        account_uuid = parsed.get("account_uuid")
        return account_uuid if isinstance(account_uuid, str) else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
```

- [ ] **Step 4: Run tests to verify the `extract_account_uuid` tests pass**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/model_routing/test_account_directory.py::TestExtractAccountUuid -v`
Expected: all 8 tests PASS. The `AccountDirectory` import will still fail at collection time — that's expected, fixed in the next step.

- [ ] **Step 5: Write the failing tests for `AccountDirectory`**

Append to `tests/gateway/routers/model_routing/test_account_directory.py`:

```python
class TestAccountDirectoryInitialization:
    """Tests for AccountDirectory initialization."""

    def test_init_with_defaults(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=True
        )
        assert directory._mongo_uri == "mongodb://localhost:27017"
        assert directory._db_name == "llm_storage"
        assert directory._collection_name == "account_directory"
        assert directory._enabled is True

    def test_init_with_custom_values(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017",
            db_name="custom_db",
            collection_name="custom_collection",
            enabled=True,
        )
        assert directory._db_name == "custom_db"
        assert directory._collection_name == "custom_collection"

    def test_init_disabled_does_not_connect(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        assert directory._enabled is False
        assert directory._client is None


class TestAccountDirectoryResolveEmail:
    """Tests for AccountDirectory.resolve_email."""

    async def test_resolve_email_found(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(
                return_value={"_id": "acct-123", "email": "person@example.com"}
            )
            result = await directory.resolve_email("acct-123")
            assert result == "person@example.com"
            directory._collection.find_one.assert_called_once_with(
                {"_id": "acct-123"}
            )

    async def test_resolve_email_not_found(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(return_value=None)
            result = await directory.resolve_email("unknown-acct")
            assert result is None

    async def test_resolve_email_when_disabled_returns_none(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            # _collection stays None since _ensure_connected is mocked and never
            # actually connects.
            result = await directory.resolve_email("acct-123")
            assert result is None

    async def test_resolve_email_lookup_failure_returns_none(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(
                side_effect=RuntimeError("boom")
            )
            result = await directory.resolve_email("acct-123")
            assert result is None

    async def test_connection_failure_disables_directory(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://invalid:27017", enabled=True
        )
        with patch(
            "pymongo.AsyncMongoClient", side_effect=RuntimeError("connection failed")
        ):
            await directory._ensure_connected()
            assert directory._enabled is False
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/model_routing/test_account_directory.py -v`
Expected: FAIL — `ImportError: cannot import name 'AccountDirectory'`

- [ ] **Step 7: Implement `AccountDirectory`**

Append to `language_model_gateway/gateway/routers/model_routing/account_directory.py`:

```python
class AccountDirectory:
    """Resolves an account_uuid to an email via a manually populated Mongo collection."""

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "account_directory",
        enabled: bool = True,
    ) -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._collection_name = collection_name
        self._enabled = enabled
        self._client: Any | None = None
        self._db: Any | None = None
        self._collection: Any | None = None

    async def _ensure_connected(self) -> None:
        """Ensure MongoDB connection is established."""
        if not self._enabled or self._collection is not None:
            return

        try:
            # Import pymongo in the function to avoid hard dependency
            from pymongo import AsyncMongoClient

            self._client = AsyncMongoClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            self._collection = self._db[self._collection_name]
            logger.info(
                "[account_directory] Connected to MongoDB: %s.%s",
                self._db_name,
                self._collection_name,
            )
        except Exception as e:
            logger.warning(
                "[account_directory] Failed to connect to MongoDB: %s. "
                "Account directory lookups will be disabled.",
                e,
            )
            self._enabled = False

    async def resolve_email(self, account_uuid: str) -> str | None:
        """Look up the email for an account_uuid. Returns None on any failure."""
        await self._ensure_connected()

        if self._collection is None:
            return None

        try:
            doc = await self._collection.find_one({"_id": account_uuid})
        except Exception as e:
            logger.warning(
                "[account_directory] Failed to resolve account_uuid: %s",
                e,
                exc_info=True,
            )
            return None

        if not doc:
            return None

        email = doc.get("email")
        return email if isinstance(email, str) else None

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[account_directory] MongoDB connection closed")
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/model_routing/test_account_directory.py -v`
Expected: all tests PASS (14 total: 8 for `extract_account_uuid`, 3 init, 5 `resolve_email`/connection).

- [ ] **Step 9: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/account_directory.py tests/gateway/routers/model_routing/test_account_directory.py
git commit -m "Add AccountDirectory for resolving Claude Code account_uuid to email"
```

---

### Task 2: Wire `AccountDirectory` into `CodingModelRouter`

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/router.py:1-125` (imports, `__init__`)
- Modify: `language_model_gateway/gateway/routers/model_routing/router.py:146-182` (`proxy_messages`, new `_enrich_with_account_directory` method)
- Test: `tests/gateway/routers/test_coding_model_router.py`

**Interfaces:**
- Consumes: `AccountDirectory.__init__(mongo_uri, db_name, collection_name, enabled)`, `AccountDirectory.resolve_email(account_uuid: str) -> str | None`, `extract_account_uuid(body_json: dict[str, Any]) -> str | None` (Task 1)
- Produces: `CodingModelRouter.__init__` gains `account_directory_collection_name: str = "account_directory"` keyword arg; `CodingModelRouter._account_directory: AccountDirectory | None` attribute; `CodingModelRouter._enrich_with_account_directory(self, auth_info: dict[str, Any], body_json: dict[str, Any]) -> None` method (mutates `auth_info` in place, returns nothing).

- [ ] **Step 1: Write the failing test for `_enrich_with_account_directory`**

Add to `tests/gateway/routers/test_coding_model_router.py` (near the existing `test_get_auth_info_*` tests around line 314-395 — same file, same style: construct `CodingModelRouter()` directly, no HTTP layer):

```python
from unittest.mock import AsyncMock

from language_model_gateway.gateway.routers.model_routing.account_directory import (
    AccountDirectory,
)


async def test_enrich_with_account_directory_fills_in_missing_user_id() -> None:
    """Should resolve account_uuid to email and set user_id/email when unset."""
    router = CodingModelRouter()
    router._account_directory = AsyncMock(spec=AccountDirectory)
    router._account_directory.resolve_email.return_value = "person@example.com"

    auth_info: dict[str, object] = {}
    body_json = {
        "metadata": {
            "user_id": '{"account_uuid": "acct-123", "device_id": "d", "session_id": "s"}'
        }
    }

    await router._enrich_with_account_directory(auth_info, body_json)

    assert auth_info["user_id"] == "person@example.com"
    assert auth_info["email"] == "person@example.com"
    router._account_directory.resolve_email.assert_awaited_once_with("acct-123")


async def test_enrich_with_account_directory_does_not_override_verified_identity() -> None:
    """Should leave auth_info alone when OIDC-verified user_id is already set."""
    router = CodingModelRouter()
    router._account_directory = AsyncMock(spec=AccountDirectory)
    router._account_directory.resolve_email.return_value = "person@example.com"

    auth_info: dict[str, object] = {"user_id": "verified-subject"}
    body_json = {
        "metadata": {"user_id": '{"account_uuid": "acct-123"}'}
    }

    await router._enrich_with_account_directory(auth_info, body_json)

    assert auth_info["user_id"] == "verified-subject"
    assert "email" not in auth_info
    router._account_directory.resolve_email.assert_not_awaited()


async def test_enrich_with_account_directory_noop_when_no_directory_configured() -> None:
    """Should be a no-op when no mongo_uri was configured (no AccountDirectory)."""
    router = CodingModelRouter()
    assert router._account_directory is None

    auth_info: dict[str, object] = {}
    body_json = {"metadata": {"user_id": '{"account_uuid": "acct-123"}'}}

    await router._enrich_with_account_directory(auth_info, body_json)

    assert auth_info == {}


async def test_enrich_with_account_directory_noop_when_account_uuid_missing() -> None:
    """Should be a no-op when the request body has no resolvable account_uuid."""
    router = CodingModelRouter()
    router._account_directory = AsyncMock(spec=AccountDirectory)

    auth_info: dict[str, object] = {}
    body_json: dict[str, object] = {}

    await router._enrich_with_account_directory(auth_info, body_json)

    assert auth_info == {}
    router._account_directory.resolve_email.assert_not_awaited()


async def test_enrich_with_account_directory_noop_when_email_not_resolved() -> None:
    """Should be a no-op when the directory has no entry for this account_uuid."""
    router = CodingModelRouter()
    router._account_directory = AsyncMock(spec=AccountDirectory)
    router._account_directory.resolve_email.return_value = None

    auth_info: dict[str, object] = {}
    body_json = {"metadata": {"user_id": '{"account_uuid": "acct-123"}'}}

    await router._enrich_with_account_directory(auth_info, body_json)

    assert auth_info == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -k enrich_with_account_directory -v`
Expected: FAIL — `AttributeError: 'CodingModelRouter' object has no attribute '_account_directory'`

- [ ] **Step 3: Add the import and constructor wiring in `router.py`**

In `language_model_gateway/gateway/routers/model_routing/router.py`, change the import block (currently line 77):

```python
from .usage_tracker import UsageTracker
```

to:

```python
from .account_directory import AccountDirectory, extract_account_uuid
from .usage_tracker import UsageTracker
```

Change the `__init__` signature (currently lines 91-102):

```python
    def __init__(
        self,
        *,
        prefix: str = "/v1",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        mongo_uri: str | None = None,
        usage_db_name: str = "llm_storage",
        usage_collection_name: str = "usage",
        token_reader: TokenReader | None = None,
        debug_log_received_oauth_tokens: bool = False,
    ) -> None:
```

to:

```python
    def __init__(
        self,
        *,
        prefix: str = "/v1",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        mongo_uri: str | None = None,
        usage_db_name: str = "llm_storage",
        usage_collection_name: str = "usage",
        account_directory_collection_name: str = "account_directory",
        token_reader: TokenReader | None = None,
        debug_log_received_oauth_tokens: bool = False,
    ) -> None:
```

Change the constructor body (currently lines 117-124):

```python
        self._usage_tracker: UsageTracker | None = None
        if mongo_uri:
            self._usage_tracker = UsageTracker(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=usage_collection_name,
                enabled=True,
            )
```

to:

```python
        self._usage_tracker: UsageTracker | None = None
        self._account_directory: AccountDirectory | None = None
        if mongo_uri:
            self._usage_tracker = UsageTracker(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=usage_collection_name,
                enabled=True,
            )
            self._account_directory = AccountDirectory(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=account_directory_collection_name,
                enabled=True,
            )
```

- [ ] **Step 4: Add the `_enrich_with_account_directory` method**

Add this new method to `router.py`, directly above the existing `async def _get_auth_info` method (currently at line 751):

```python
    async def _enrich_with_account_directory(
        self, auth_info: dict[str, Any], body_json: dict[str, Any]
    ) -> None:
        """Best-effort attribution fallback via Claude Code's account_uuid.

        _get_auth_info only populates auth_info["user_id"] when the caller's
        Authorization header verifies as a genuine OIDC token — which never
        happens for real Claude Code traffic, since that header is always the
        client's own Anthropic subscription OAuth token. This fills the gap
        using a manually-populated account_uuid -> email directory, but only
        when the OIDC-verified path left user_id unset; verified identity
        always wins when present.
        """
        if auth_info.get("user_id") or self._account_directory is None:
            return

        account_uuid = extract_account_uuid(body_json)
        if account_uuid is None:
            return

        email = await self._account_directory.resolve_email(account_uuid)
        if email:
            auth_info["user_id"] = email
            auth_info["email"] = email
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -k enrich_with_account_directory -v`
Expected: all 5 tests PASS.

- [ ] **Step 6: Call the new method from `proxy_messages`**

In `router.py`, change (currently lines 179-181):

```python
        auth_info = await self._get_auth_info(request)
        user_id = auth_info.get("user_id", "unknown")
        auth_provider = auth_info.get("auth_provider", "unknown")
```

to:

```python
        auth_info = await self._get_auth_info(request)
        await self._enrich_with_account_directory(auth_info, body_json)
        user_id = auth_info.get("user_id", "unknown")
        auth_provider = auth_info.get("auth_provider", "unknown")
```

- [ ] **Step 7: Run the full router test suite to check nothing broke**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py tests/gateway/routers/model_routing/ -v`
Expected: all tests PASS (existing tests + the 5 new ones + the 14 from Task 1).

- [ ] **Step 8: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/router.py tests/gateway/routers/test_coding_model_router.py
git commit -m "Wire AccountDirectory into CodingModelRouter for usage attribution fallback"
```

---

### Task 3: Environment variable + `api.py` wiring

**Files:**
- Modify: `language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py:133-145`
- Modify: `language_model_gateway/gateway/api.py:192-200`

**Interfaces:**
- Consumes: `CodingModelRouter.__init__`'s `account_directory_collection_name` kwarg (Task 2)
- Produces: `LanguageModelGatewayEnvironmentVariables.model_routing_account_directory_collection_name -> str` property

- [ ] **Step 1: Add the property**

In `language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py`, after the existing `model_routing_usage_collection_name` property (currently ending at line 145), add:

```python
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
```

- [ ] **Step 2: Wire it into `api.py`**

In `language_model_gateway/gateway/api.py`, change (currently lines 192-200):

```python
    app1.include_router(
        CodingModelRouter(
            mongo_uri=mongo_llm_storage_uri,
            usage_db_name=env_vars.mongo_llm_storage_db_name or "llm_storage",
            usage_collection_name=env_vars.model_routing_usage_collection_name,
            token_reader=container.resolve(TokenReader),
            debug_log_received_oauth_tokens=env_vars.debug_log_received_oauth_tokens,
        ).get_router()
    )
```

to:

```python
    app1.include_router(
        CodingModelRouter(
            mongo_uri=mongo_llm_storage_uri,
            usage_db_name=env_vars.mongo_llm_storage_db_name or "llm_storage",
            usage_collection_name=env_vars.model_routing_usage_collection_name,
            account_directory_collection_name=(
                env_vars.model_routing_account_directory_collection_name
            ),
            token_reader=container.resolve(TokenReader),
            debug_log_received_oauth_tokens=env_vars.debug_log_received_oauth_tokens,
        ).get_router()
    )
```

- [ ] **Step 3: Verify the app still constructs cleanly**

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway python3 -c "import ast; ast.parse(open('language_model_gateway/gateway/api.py').read())" && echo OK`
Expected: `OK`

Run: `docker compose run --rm --name lmg_plan_step language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q`
Expected: all tests PASS (this file's tests exercise `CodingModelRouter` directly and would fail on a constructor signature error).

- [ ] **Step 4: Commit**

```bash
git add language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py language_model_gateway/gateway/api.py
git commit -m "Add MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME env var"
```

---

### Task 4: Documentation

**Files:**
- Modify: `docs/coding_model_router.md`

**Interfaces:**
- Consumes: nothing (documentation only)

- [ ] **Step 1: Add the env var row**

In `docs/coding_model_router.md`, in the "Environment variables" table, change (currently line 72):

```markdown
| `MODEL_ROUTING_USAGE_COLLECTION_NAME` | `model-router-usage` | Collection name for usage-tracking records within that database. |
```

to add a new row directly after it:

```markdown
| `MODEL_ROUTING_USAGE_COLLECTION_NAME` | `model-router-usage` | Collection name for usage-tracking records within that database. |
| `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME` | `model-router-account-directory` | Collection name for the manually-populated account_uuid → email lookup table (see "Usage tracking" below). |
```

- [ ] **Step 2: Extend the "Usage tracking" section**

In `docs/coding_model_router.md`, in the "Usage tracking" section, after the existing "Attribution" paragraph (currently ending "...usage is still recorded, just without a `user_id`." around line 292) and before the "**Never blocks the response:**" paragraph, insert:

```markdown
**Fallback attribution via account directory:** for real Claude Code traffic, the
OIDC-verification path above never actually applies — Claude Code's `Authorization`
header is always the client's own Anthropic subscription OAuth token, never a
b.well-issued JWT, so it never verifies. Every Claude Code request does carry an
opaque `account_uuid` in `body.metadata.user_id` (a JSON string Claude Code sends
automatically), but Anthropic doesn't expose any API to resolve that to a human
email. When `MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME`'s collection has a
manually-imported `{_id: account_uuid, email}` document for that `account_uuid`
(populated from an Anthropic/Claude Console admin export — there is no import
tooling in this repo, load it directly with `mongoimport`/Compass), that email is
used for `user_id`/`email` on the usage record instead. The OIDC-verified path
always wins when it does apply; this is purely a fallback for when it doesn't.
```

- [ ] **Step 3: Verify markdown renders sensibly**

Run: `cat docs/coding_model_router.md | grep -A3 "MODEL_ROUTING_ACCOUNT_DIRECTORY"`
Expected: shows the new table row and the new paragraph's opening line.

- [ ] **Step 4: Commit**

```bash
git add docs/coding_model_router.md
git commit -m "Document account directory fallback attribution"
```

---

### Task 5: Helm chart

**Files:**
- Modify: `/Users/imranqureshi/git/helm.helix-service/.helm/language-model-gateway/services.values.yaml`

**Interfaces:**
- Consumes: nothing (deployment config only)

- [ ] **Step 1: Create a branch**

```bash
cd /Users/imranqureshi/git/helm.helix-service
git checkout main && git pull --ff-only
git checkout -b add-model-routing-account-directory-collection-name
```

- [ ] **Step 2: Add the env var**

In `.helm/language-model-gateway/services.values.yaml`, change (currently lines 166-167):

```yaml
    - name: MODEL_ROUTING_USAGE_COLLECTION_NAME
      value: "model-router-usage"
```

to add a new entry directly after it:

```yaml
    - name: MODEL_ROUTING_USAGE_COLLECTION_NAME
      value: "model-router-usage"
    - name: MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME
      value: "model-router-account-directory"
```

- [ ] **Step 3: Commit and push**

```bash
git add .helm/language-model-gateway/services.values.yaml
git commit -m "Add MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME for language-model-gateway"
git push -u origin add-model-routing-account-directory-collection-name
```

- [ ] **Step 4: Open a PR**

```bash
gh pr create --repo icanbwell/helm.helix-service \
  --title "Add MODEL_ROUTING_ACCOUNT_DIRECTORY_COLLECTION_NAME for language-model-gateway" \
  --body "$(cat <<'EOF'
## Summary
- language-model-gateway now resolves Claude Code's account_uuid to an email via a
  manually-populated Mongo lookup table, used as fallback usage-tracking attribution
  when the OIDC-verified identity path doesn't apply (which is the common case for
  Claude Code traffic).
- Adds the collection-name env var alongside its siblings. Not a behavior change on
  its own — the collection starts empty until manually populated.

## Test plan
- [ ] Deploy to a non-prod environment and confirm the app still starts (missing
      collection/empty directory must not break anything)
EOF
)"
```

---

## Final check across all tasks

- [ ] Run the full targeted test suite one more time: `docker compose run --rm --name lmg_plan_final language-model-gateway pytest tests/gateway/routers/ -q`
- [ ] Confirm `git log --oneline -6` on `language-model-gateway` shows the 4 commits from Tasks 1-4 in order
- [ ] Confirm the helm PR from Task 5 is open
