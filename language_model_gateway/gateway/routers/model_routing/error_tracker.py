"""Error tracking for model routing - records upstream failures to MongoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_ERROR_MESSAGE_LIMIT = 1000


class ErrorTracker:
    """Tracks and records upstream request failures to MongoDB for model routing.

    Sibling of UsageTracker, same lazy-connect/fire-and-forget/never-raise
    posture — a failure to write an error record must never mask or replace
    the original error being recorded.
    """

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "errors",
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
                "[error_tracker] Connected to MongoDB: %s.%s",
                self._db_name,
                self._collection_name,
            )
        except Exception as e:
            logger.warning(
                "[error_tracker] Failed to connect to MongoDB: %s. "
                "Error tracking will be disabled.",
                e,
            )
            self._enabled = False

    async def record_error(
        self,
        request_id: str,
        model: str,
        error_type: str,
        error_message: str,
        start_time: datetime,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        account_uuid: str | None = None,
        agent_id: str | None = None,
        parent_agent_id: str | None = None,
        model_tier: str | None = None,
        backend: str | None = None,
        auth: str | None = None,
        api_type: str | None = None,
        streaming: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        """Record an upstream request failure to MongoDB.

        `error_message` is truncated to `_ERROR_MESSAGE_LIMIT` chars — the
        message is for triage/trend-spotting, not full incident replay, and
        upstream error bodies can otherwise be arbitrarily large.
        """
        await self._ensure_connected()

        if self._collection is None:
            return

        end_time = datetime.now(timezone.utc)
        error_record: dict[str, Any] = {
            "request_id": request_id,
            "model": model,
            "error_type": error_type,
            "error_message": error_message[:_ERROR_MESSAGE_LIMIT],
            "timestamp": end_time,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": round((end_time - start_time).total_seconds() * 1000, 3),
        }
        if user_id:
            error_record["user_id"] = user_id
        if session_id:
            error_record["session_id"] = session_id
        if account_uuid:
            error_record["account_uuid"] = account_uuid
        if agent_id:
            error_record["agent_id"] = agent_id
        if parent_agent_id:
            error_record["parent_agent_id"] = parent_agent_id
        if model_tier:
            error_record["model_tier"] = model_tier
        if backend:
            error_record["backend"] = backend
        if auth:
            error_record["auth"] = auth
        if api_type:
            error_record["api_type"] = api_type
        if streaming is not None:
            error_record["streaming"] = streaming
        if status_code is not None:
            error_record["status_code"] = status_code

        try:
            await self._collection.insert_one(error_record)
        except Exception as e:
            logger.warning(
                "[error_tracker] Failed to record error: %s",
                e,
                exc_info=True,
            )

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[error_tracker] MongoDB connection closed")
