"""Read-only access to the per-session usage rollup for model routing.

Mirrors account_directory.py's connect-lazily/disable-on-failure pattern,
but reads usage_tracker.py's `model-router-sessions` rollup collection
instead of the account directory. Deliberately kept separate from
`UsageTracker` (which only ever writes) so a read-only consumer never
depends on an interface that also exposes insert/upsert methods.
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
    backend: str | None
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
                backend=doc.get(f"{bucket}_tier_backend"),
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
