# Session Savings Statusline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a Claude Code statusline message with this session's model-routing cost savings (total $ saved vs. Anthropic list price, plus a per-tier breakdown), fed by a new read-only gateway endpoint.

**Architecture:** A new `SessionSavingsReader` reads the `model-router-sessions` rollup collection that `usage_tracker.py` already maintains per `session_id`. A new `SessionSavingsRouter` exposes it at `GET /v1/model-routing/sessions/{session_id}/savings`, mounted in `api.py` alongside the existing `CodingModelRouter`. A small Python statusline script (no new dependencies) reads Claude Code's stdin payload, calls that endpoint, and prints a formatted line.

**Tech Stack:** FastAPI, Pydantic, `pymongo` (`AsyncMongoClient`, already a dependency), Python stdlib `urllib.request` for the statusline script (deliberately no `requests`/`httpx` dependency for the script, since it must be runnable standalone on a developer's machine with only stdlib).

## Global Constraints

- No new auth scheme: the endpoint is gated only by `session_id` being an unguessable UUIDv4 — see the design doc's "Security posture" section. Do not add a shared-secret header, API key, or any other custom credential to this endpoint.
- No new third-party dependency for the statusline script — stdlib only (`json`, `urllib.request`).
- Reuse the *existing* env vars already wired to `CodingModelRouter` in `api.py` (`mongo_llm_storage_uri`, `mongo_llm_storage_db_name`, `model_routing_usage_session_collection_name`) — do not introduce new env vars for Mongo connectivity; the reader must point at the same collection the writer uses.
- Follow the existing `AccountDirectory`/`UsageTracker` pattern exactly: lazy-connect `_ensure_connected()`, disable-self-on-failure (never raise into the request path), deferred `from pymongo import AsyncMongoClient` import.
- Full spec: `docs/superpowers/specs/2026-07-16-session-savings-statusline-design.md`.

---

### Task 1: `SessionSavingsReader`

**Files:**
- Create: `language_model_gateway/gateway/routers/model_routing/session_savings_reader.py`
- Test: `tests/gateway/routers/model_routing/test_session_savings_reader.py`

**Interfaces:**
- Produces: `TierSavings` (Pydantic model: `model: str | None`, `cost_usd: float`, `anthropic_cost_usd: float`), `SessionSavings` (Pydantic model: `session_id: str`, `total_savings_usd: float`, `total_tokens: int`, `tiers: dict[str, TierSavings]`), `SessionSavingsReader` with constructor `(mongo_uri: str, db_name: str = "llm_storage", collection_name: str = "model-router-sessions", enabled: bool = True)` and `async def get_session_savings(self, session_id: str) -> SessionSavings | None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/gateway/routers/model_routing/test_session_savings_reader.py`:

```python
"""
Tests for session_savings_reader.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavingsReader,
)


class TestSessionSavingsReaderInitialization:
    def test_init_with_defaults(self) -> None:
        reader = SessionSavingsReader(mongo_uri="mongodb://localhost:27017")
        assert reader._mongo_uri == "mongodb://localhost:27017"
        assert reader._db_name == "llm_storage"
        assert reader._collection_name == "model-router-sessions"
        assert reader._enabled is True

    def test_init_disabled_does_not_connect(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        assert reader._enabled is False
        assert reader._client is None


class TestSessionSavingsReaderGetSessionSavings:
    async def test_returns_savings_with_all_tiers(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        doc = {
            "session_id": "sess-1",
            "total_savings_usd": 0.42,
            "total_tokens": 12345,
            "low_tier_model": "qwen-coder",
            "low_tier_cost": 0.10,
            "low_tier_anthropic_cost": 0.30,
            "medium_tier_model": "claude-sonnet-5",
            "medium_tier_cost": 0.30,
            "medium_tier_anthropic_cost": 0.50,
            "high_tier_model": "claude-opus-4-8",
            "high_tier_cost": 0.02,
            "high_tier_anthropic_cost": 0.06,
        }
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=doc)

            result = await reader.get_session_savings("sess-1")

            assert result is not None
            assert result.session_id == "sess-1"
            assert result.total_savings_usd == 0.42
            assert result.total_tokens == 12345
            assert set(result.tiers.keys()) == {"low", "medium", "high"}
            assert result.tiers["low"].model == "qwen-coder"
            assert result.tiers["low"].cost_usd == 0.10
            assert result.tiers["low"].anthropic_cost_usd == 0.30
            reader._collection.find_one.assert_called_once_with(
                {"session_id": "sess-1"}
            )

    async def test_omits_tiers_the_session_never_used(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        doc = {
            "session_id": "sess-2",
            "total_savings_usd": 0.10,
            "total_tokens": 500,
            "low_tier_model": "qwen-coder",
            "low_tier_cost": 0.05,
            "low_tier_anthropic_cost": 0.15,
        }
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=doc)

            result = await reader.get_session_savings("sess-2")

            assert result is not None
            assert set(result.tiers.keys()) == {"low"}

    async def test_returns_none_when_session_not_found(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=None)

            result = await reader.get_session_savings("unknown-session")

            assert result is None

    async def test_returns_none_when_disabled(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            # _collection stays None since _ensure_connected is mocked and
            # never actually connects.
            result = await reader.get_session_savings("sess-1")
            assert result is None

    async def test_returns_none_on_lookup_failure(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(side_effect=RuntimeError("boom"))

            result = await reader.get_session_savings("sess-1")

            assert result is None

    async def test_connection_failure_disables_reader(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://invalid:27017", enabled=True
        )
        with patch(
            "pymongo.AsyncMongoClient", side_effect=RuntimeError("connection failed")
        ):
            await reader._ensure_connected()
            assert reader._enabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/model_routing/test_session_savings_reader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'language_model_gateway.gateway.routers.model_routing.session_savings_reader'`

- [ ] **Step 3: Write the implementation**

Create `language_model_gateway/gateway/routers/model_routing/session_savings_reader.py`:

```python
"""Read-only access to the per-session usage rollup for model routing.

Mirrors account_directory.py's connect-lazily/disable-on-failure pattern,
but reads usage_tracker.py's `model-router-sessions` rollup collection instead of
the account directory. Deliberately kept separate from `UsageTracker` (which
only ever writes) so a read-only consumer never depends on an interface
that also exposes insert/upsert methods.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Mirrors usage_tracker.py's _TIER_TO_SESSION_BUCKET value set — the session
# rollup document buckets cost by these four tier names.
_TIER_BUCKETS: tuple[str, ...] = ("low", "medium", "high", "fable")


class TierSavings(BaseModel):
    model: str | None
    cost_usd: float
    anthropic_cost_usd: float


class SessionSavings(BaseModel):
    session_id: str
    total_savings_usd: float
    total_tokens: int
    tiers: dict[str, TierSavings]


class SessionSavingsReader:
    """Read-only reader for the model-router-sessions rollup collection."""

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "model-router-sessions",
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
            # Deferred import: skip pymongo's import cost when this feature
            # is disabled (no mongo_uri configured), since _ensure_connected
            # is then never called.
            from pymongo import AsyncMongoClient

            self._client = AsyncMongoClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            self._collection = self._db[self._collection_name]
            logger.info(
                "[session_savings_reader] Connected to MongoDB: %s.%s",
                self._db_name,
                self._collection_name,
            )
        except Exception as e:
            logger.warning(
                "[session_savings_reader] Failed to connect to MongoDB: %s. "
                "Session savings lookups will be disabled.",
                e,
            )
            self._enabled = False

    async def get_session_savings(self, session_id: str) -> SessionSavings | None:
        """Look up the savings rollup for a session_id.

        Returns None if the session has no rollup yet (e.g. its first
        request is still in flight, or the id is unknown) or on any Mongo
        failure — this never raises into the caller.
        """
        await self._ensure_connected()

        if self._collection is None:
            return None

        try:
            doc = await self._collection.find_one({"session_id": session_id})
        except Exception as e:
            logger.warning(
                "[session_savings_reader] Failed to look up session %s: %s",
                session_id,
                e,
                exc_info=True,
            )
            return None

        if not doc:
            return None

        tiers: dict[str, TierSavings] = {}
        for bucket in _TIER_BUCKETS:
            cost = doc.get(f"{bucket}_tier_cost")
            if cost is None:
                continue
            tiers[bucket] = TierSavings(
                model=doc.get(f"{bucket}_tier_model"),
                cost_usd=cost,
                anthropic_cost_usd=doc.get(f"{bucket}_tier_anthropic_cost", 0.0),
            )

        return SessionSavings(
            session_id=session_id,
            total_savings_usd=doc.get("total_savings_usd", 0.0),
            total_tokens=doc.get("total_tokens", 0),
            tiers=tiers,
        )

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[session_savings_reader] MongoDB connection closed")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/model_routing/test_session_savings_reader.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/session_savings_reader.py tests/gateway/routers/model_routing/test_session_savings_reader.py
git commit -m "Add SessionSavingsReader for model-routing session cost rollups"
```

---

### Task 2: `SessionSavingsRouter`

**Files:**
- Create: `language_model_gateway/gateway/routers/model_routing/session_savings_router.py`
- Test: `tests/gateway/routers/model_routing/test_session_savings_router.py`

**Interfaces:**
- Consumes: `SessionSavings`, `SessionSavingsReader` from Task 1 (`language_model_gateway.gateway.routers.model_routing.session_savings_reader`).
- Produces: `SessionSavingsRouter` with constructor `(*, prefix: str = "/v1/model-routing", tags: list[str | Enum] | None = None, dependencies: Sequence[params.Depends] | None = None, mongo_uri: str | None = None, db_name: str = "llm_storage", collection_name: str = "model-router-sessions")` and `get_router() -> APIRouter`, registering `GET {prefix}/sessions/{session_id}/savings`.

- [ ] **Step 1: Write the failing tests**

Create `tests/gateway/routers/model_routing/test_session_savings_router.py`:

```python
"""
Tests for session_savings_router.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavings,
    TierSavings,
)
from language_model_gateway.gateway.routers.model_routing.session_savings_router import (
    SessionSavingsRouter,
)


def test_registers_savings_route() -> None:
    router = SessionSavingsRouter()
    paths = {r.path for r in router.get_router().routes if isinstance(r, APIRoute)}
    assert "/v1/model-routing/sessions/{session_id}/savings" in paths


@pytest.mark.asyncio
async def test_get_savings_returns_200_with_body() -> None:
    router = SessionSavingsRouter(mongo_uri="mongodb://localhost:27017")
    savings = SessionSavings(
        session_id="sess-1",
        total_savings_usd=0.42,
        total_tokens=12345,
        tiers={"low": TierSavings(model="qwen-coder", cost_usd=0.10, anthropic_cost_usd=0.30)},
    )
    app = FastAPI()
    app.include_router(router.get_router())

    with patch.object(
        router._reader, "get_session_savings", new=AsyncMock(return_value=savings)
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/model-routing/sessions/sess-1/savings")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "sess-1"
    assert body["total_savings_usd"] == 0.42
    assert body["tiers"]["low"]["cost_usd"] == 0.10


@pytest.mark.asyncio
async def test_get_savings_returns_404_when_not_found() -> None:
    router = SessionSavingsRouter(mongo_uri="mongodb://localhost:27017")
    app = FastAPI()
    app.include_router(router.get_router())

    with patch.object(
        router._reader, "get_session_savings", new=AsyncMock(return_value=None)
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/model-routing/sessions/unknown/savings")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_savings_returns_404_when_no_mongo_configured() -> None:
    router = SessionSavingsRouter(mongo_uri=None)
    app = FastAPI()
    app.include_router(router.get_router())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/model-routing/sessions/sess-1/savings")

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/model_routing/test_session_savings_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'language_model_gateway.gateway.routers.model_routing.session_savings_router'`

- [ ] **Step 3: Write the implementation**

Create `language_model_gateway/gateway/routers/model_routing/session_savings_router.py`:

```python
"""Read-only endpoint for a Claude Code session's model-routing savings.

Deliberately unauthenticated (session_id-as-capability) — see
docs/superpowers/specs/2026-07-16-session-savings-statusline-design.md
("Security posture") for the reasoning. Returns only an aggregate cost
figure — no prompt/response content, no PHI, no email/account identity.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Sequence

from fastapi import APIRouter, HTTPException, params

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavings,
    SessionSavingsReader,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_NOT_FOUND_DETAIL = "no usage recorded for this session"


class SessionSavingsRouter:
    """Exposes GET {prefix}/sessions/{session_id}/savings."""

    def __init__(
        self,
        *,
        prefix: str = "/v1/model-routing",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        mongo_uri: str | None = None,
        db_name: str = "llm_storage",
        collection_name: str = "model-router-sessions",
    ) -> None:
        self.router = APIRouter(
            prefix=prefix,
            tags=tags or ["model-routing-savings"],
            dependencies=dependencies or [],
        )
        self._reader: SessionSavingsReader | None = None
        if mongo_uri:
            self._reader = SessionSavingsReader(
                mongo_uri=mongo_uri,
                db_name=db_name,
                collection_name=collection_name,
                enabled=True,
            )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/sessions/{session_id}/savings",
            self.get_session_savings,
            methods=["GET"],
            response_model=SessionSavings,
            summary="Get model-routing savings for a Claude Code session",
            description=(
                "Returns this gateway's cumulative cost savings (vs. "
                "Anthropic list price) for the given Claude Code session_id, "
                "broken down by model tier."
            ),
            status_code=200,
        )

    async def get_session_savings(self, session_id: str) -> SessionSavings:
        if self._reader is None:
            raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
        savings = await self._reader.get_session_savings(session_id)
        if savings is None:
            raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
        return savings

    def get_router(self) -> APIRouter:
        return self.router
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/model_routing/test_session_savings_router.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/session_savings_router.py tests/gateway/routers/model_routing/test_session_savings_router.py
git commit -m "Add SessionSavingsRouter exposing GET /v1/model-routing/sessions/{session_id}/savings"
```

---

### Task 3: Wire `SessionSavingsRouter` into `api.py`

**Files:**
- Modify: `language_model_gateway/gateway/api.py:32` (imports), `language_model_gateway/gateway/api.py:222` (include_router calls)
- Test: `tests/gateway/routers/test_session_savings_wiring.py`

**Interfaces:**
- Consumes: `SessionSavingsRouter` from Task 2. `env_vars.mongo_llm_storage_uri`, `env_vars.mongo_llm_storage_db_name`, `env_vars.model_routing_usage_session_collection_name` — all already defined properties on `LanguageModelGatewayEnvironmentVariables` (used identically by the existing `CodingModelRouter(...)` construction a few lines above).

- [ ] **Step 1: Write the failing test**

Create `tests/gateway/routers/test_session_savings_wiring.py`:

```python
"""
Verifies the session-savings route is mounted by create_app().
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from language_model_gateway.gateway.api import create_app


def test_session_savings_route_is_mounted() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/v1/model-routing/sessions/{session_id}/savings" in paths
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/test_session_savings_wiring.py -v`
Expected: FAIL — `assert "/v1/model-routing/sessions/{session_id}/savings" in paths` (route not present)

- [ ] **Step 3: Add the import and mount the router**

In `language_model_gateway/gateway/api.py`, add the import next to the existing `model_routing.router` import (around line 32):

```python
from language_model_gateway.gateway.routers.model_routing.router import (
    CodingModelRouter,
)
from language_model_gateway.gateway.routers.model_routing.session_savings_router import (
    SessionSavingsRouter,
)
```

Then, immediately after the existing `app1.include_router(CodingModelRouter(...).get_router())` call (right before `app1.include_router(ChatCompletionsRouter().get_router())`, around line 222), add:

```python
    app1.include_router(
        SessionSavingsRouter(
            mongo_uri=mongo_llm_storage_uri,
            db_name=env_vars.mongo_llm_storage_db_name or "llm_storage",
            collection_name=env_vars.model_routing_usage_session_collection_name,
        ).get_router()
    )
```

This reuses `mongo_llm_storage_uri` — the same already-credentialed URI variable computed a few lines earlier via `MongoUrlHelpers.add_credentials_to_mongo_url(...)` for `CodingModelRouter` — so the reader and the writer connect to the exact same Mongo instance and collection.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/gateway/routers/test_session_savings_wiring.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests -v`
Expected: PASS (no regressions in existing `api.py`/router tests)

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/api.py tests/gateway/routers/test_session_savings_wiring.py
git commit -m "Mount SessionSavingsRouter in create_app()"
```

---

### Task 4: Statusline script + settings.json wiring doc

**Files:**
- Create: `scripts/claude_code_statusline.py`
- Test: `tests/scripts/test_claude_code_statusline.py`
- Modify: `docs/model_routing_guide.md` (new section before `## Key Points`, currently at line 152)

**Interfaces:**
- Consumes: the JSON response shape produced by Task 2's endpoint (`session_id`, `total_savings_usd`, `total_tokens`, `tiers: {bucket: {model, cost_usd, anthropic_cost_usd}}`).
- Produces: `format_savings_line(payload: dict) -> str | None`, `fetch_savings(gateway_url: str, session_id: str) -> dict | None`, `main() -> None` — all in `scripts/claude_code_statusline.py`, importable by tests without executing the script (guarded by `if __name__ == "__main__":`).

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/__init__.py` (empty file, so pytest can import the module under test as a package-relative path):

```python
```

Create `tests/scripts/test_claude_code_statusline.py`:

```python
"""
Tests for scripts/claude_code_statusline.py.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "claude_code_statusline.py"
_spec = importlib.util.spec_from_file_location("claude_code_statusline", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
statusline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(statusline)


class TestFormatSavingsLine:
    def test_formats_total_and_tier_breakdown(self) -> None:
        payload = {
            "total_savings_usd": 0.42,
            "tiers": {
                "low": {"cost_usd": 0.10},
                "medium": {"cost_usd": 0.30},
                "high": {"cost_usd": 0.02},
            },
        }
        line = statusline.format_savings_line(payload)
        assert line is not None
        assert "0.42" in line
        assert "haiku $0.10" in line
        assert "sonnet $0.30" in line
        assert "opus $0.02" in line

    def test_formats_total_with_no_tiers(self) -> None:
        payload = {"total_savings_usd": 0.0, "tiers": {}}
        line = statusline.format_savings_line(payload)
        assert line is not None
        assert "0.00" in line

    def test_returns_none_when_total_missing(self) -> None:
        assert statusline.format_savings_line({}) is None


class TestFetchSavings:
    def test_returns_none_on_url_error(self) -> None:
        with patch.object(
            statusline.urllib.request,
            "urlopen",
            side_effect=statusline.urllib.error.URLError("boom"),
        ):
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result is None

    def test_returns_none_on_malformed_json(self) -> None:
        response = io.BytesIO(b"not json")
        cm = patch.object(statusline.urllib.request, "urlopen")
        with cm as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = response
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result is None

    def test_returns_parsed_json_on_success(self) -> None:
        payload = {"total_savings_usd": 0.42, "tiers": {}}
        response = io.BytesIO(json.dumps(payload).encode())
        cm = patch.object(statusline.urllib.request, "urlopen")
        with cm as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = response
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result == payload


class TestMain:
    def test_prints_nothing_when_stdin_is_not_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "stdin", io.StringIO("not json")):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_nothing_when_session_id_missing(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "stdin", io.StringIO(json.dumps({}))):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_nothing_when_gateway_url_unset(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MODEL_ROUTING_GATEWAY_URL", raising=False)
        with patch.object(sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-1"}))):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_line_on_success(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_ROUTING_GATEWAY_URL", "http://gateway")
        payload = {"total_savings_usd": 0.42, "tiers": {}}
        with patch.object(sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-1"}))):
            with patch.object(statusline, "fetch_savings", return_value=payload):
                statusline.main()
        assert "0.42" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/scripts/test_claude_code_statusline.py -v`
Expected: FAIL — `FileNotFoundError` (script doesn't exist yet)

- [ ] **Step 3: Write the script**

Create `scripts/claude_code_statusline.py`:

```python
#!/usr/bin/env python3
"""Claude Code statusLine command: shows this session's model-routing savings.

Reads Claude Code's statusline JSON payload from stdin (must include
session_id), calls this gateway's
GET /v1/model-routing/sessions/{session_id}/savings, and prints a one-line
summary. Any failure (timeout, network error, 404, malformed response)
prints nothing — a missing footer segment is a normal, silent outcome here,
never a stall or a raw error string in Claude Code's UI.

Configure via ~/.claude/settings.json:
  {"statusLine": {"type": "command", "command": "python3 /path/to/claude_code_statusline.py"}}
and set MODEL_ROUTING_GATEWAY_URL to this gateway's base URL in your shell env.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

_TIMEOUT_SECONDS = 2.0
_TIER_LABELS = {"low": "haiku", "medium": "sonnet", "high": "opus", "fable": "fable"}


def format_savings_line(payload: dict) -> str | None:
    """Format the endpoint's JSON body into a one-line statusline message."""
    total_savings = payload.get("total_savings_usd")
    if total_savings is None:
        return None
    tiers = payload.get("tiers") or {}
    tier_parts = [
        f"{_TIER_LABELS.get(bucket, bucket)} ${tier['cost_usd']:.2f}"
        for bucket, tier in tiers.items()
        if isinstance(tier, dict) and "cost_usd" in tier
    ]
    line = f"\U0001f4b0 ${total_savings:.2f} saved"
    if tier_parts:
        line += " (" + " · ".join(tier_parts) + ")"
    return line


def fetch_savings(gateway_url: str, session_id: str) -> dict | None:
    """GET the session's savings from the gateway. Returns None on any failure."""
    url = f"{gateway_url.rstrip('/')}/v1/model-routing/sessions/{session_id}/savings"
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def main() -> None:
    try:
        stdin_payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return
    session_id = stdin_payload.get("session_id")
    if not session_id:
        return
    gateway_url = os.environ.get("MODEL_ROUTING_GATEWAY_URL")
    if not gateway_url:
        return
    savings = fetch_savings(gateway_url, session_id)
    if savings is None:
        return
    line = format_savings_line(savings)
    if line:
        print(line)


if __name__ == "__main__":
    main()
```

Make it executable:

```bash
chmod +x scripts/claude_code_statusline.py
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm --name language-model-gateway_tests language-model-gateway pytest tests/scripts/test_claude_code_statusline.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Document the `~/.claude/settings.json` wiring**

In `docs/model_routing_guide.md`, insert a new section immediately before `## Key Points` (currently line 152):

```markdown
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
```

- [ ] **Step 6: Commit**

```bash
git add scripts/claude_code_statusline.py tests/scripts/__init__.py tests/scripts/test_claude_code_statusline.py docs/model_routing_guide.md
git commit -m "Add Claude Code statusline script for model-routing session savings"
```

---

## Self-Review Notes

- **Spec coverage:** every deliverable listed in the design doc's "Deliverables" section (reader, router, api.py wiring, script + doc snippet, tests) maps to Tasks 1–4. The design doc's already-applied docstring fixes are explicitly out of scope here (already done, not re-planned).
- **Type consistency:** `SessionSavings`/`TierSavings` are defined once in Task 1 and imported verbatim (not redefined) in Tasks 2 and referenced by field name in Task 4's script — checked `cost_usd`, `anthropic_cost_usd`, `total_savings_usd`, `total_tokens`, `tiers` are spelled identically everywhere they appear.
- **No placeholders:** every step has runnable code and an exact test command; nothing deferred to "add error handling later."
