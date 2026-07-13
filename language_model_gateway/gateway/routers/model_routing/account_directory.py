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


def _parse_claude_code_metadata(body_json: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort parse of Claude Code's request metadata blob.

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
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def extract_account_uuid(body_json: dict[str, Any]) -> str | None:
    """Best-effort extraction of Claude Code's account_uuid from request metadata."""
    parsed = _parse_claude_code_metadata(body_json)
    if parsed is None:
        return None
    account_uuid = parsed.get("account_uuid")
    return account_uuid if isinstance(account_uuid, str) else None


def extract_session_id(body_json: dict[str, Any]) -> str | None:
    """Best-effort extraction of Claude Code's session_id from request metadata.

    Unlike account_uuid, this is never used for identity or authorization —
    only to correlate usage records within a single CLI session — so it's
    safe to trust this client-supplied value even when the caller's identity
    hasn't been verified.
    """
    parsed = _parse_claude_code_metadata(body_json)
    if parsed is None:
        return None
    session_id = parsed.get("session_id")
    return session_id if isinstance(session_id, str) else None


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
        self._email_cache: dict[str, str | None] = {}

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
        """Look up the email for an account_uuid. Returns None on any failure.

        Results (including misses) are cached in-process for the lifetime of
        this instance, since the underlying directory only changes via manual
        re-import and this is called on the hot request path. A transient
        Mongo failure is cached as a miss too, same as a genuine "not in the
        directory" — it won't be retried until the process restarts.
        """
        if account_uuid in self._email_cache:
            return self._email_cache[account_uuid]

        await self._ensure_connected()

        if self._collection is None:
            self._email_cache[account_uuid] = None
            return None

        try:
            doc = await self._collection.find_one({"_id": account_uuid})
        except Exception as e:
            logger.warning(
                "[account_directory] Failed to resolve account_uuid: %s",
                e,
                exc_info=True,
            )
            self._email_cache[account_uuid] = None
            return None

        if not doc:
            self._email_cache[account_uuid] = None
            return None

        email = doc.get("email")
        result = email if isinstance(email, str) else None
        self._email_cache[account_uuid] = result
        return result

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[account_directory] MongoDB connection closed")
