"""Usage tracking for model routing - records token usage to MongoDB."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks and records token usage to MongoDB for model routing."""

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "usage",
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
                "[usage_tracker] Connected to MongoDB: %s.%s",
                self._db_name,
                self._collection_name,
            )
        except Exception as e:
            logger.warning(
                "[usage_tracker] Failed to connect to MongoDB: %s. "
                "Usage tracking will be disabled.",
                e,
            )
            self._enabled = False

    async def record_usage(
        self,
        request_id: str,
        user_id: str | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        auth_provider: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> None:
        """Record token usage to MongoDB."""
        if not self._enabled or (input_tokens == 0 and output_tokens == 0):
            return

        await self._ensure_connected()

        if self._collection is None:
            return

        usage_record: dict[str, Any] = {
            "request_id": request_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

        if user_id:
            usage_record["user_id"] = user_id
        if auth_provider:
            usage_record["auth_provider"] = auth_provider
        if email:
            usage_record["email"] = email
        if user_name:
            usage_record["user_name"] = user_name

        try:
            await self._collection.insert_one(usage_record)
            logger.debug(
                "[usage_tracker] Recorded usage: %d input, %d output tokens for %s",
                input_tokens,
                output_tokens,
                model,
            )
        except Exception as e:
            logger.warning(
                "[usage_tracker] Failed to record usage: %s",
                e,
                exc_info=True,
            )

    async def record_usage_from_anthropic_response(
        self,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        response_body: dict[str, Any],
    ) -> None:
        """Extract usage from Anthropic response and record it."""
        usage = response_body.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # auth_info's identity fields are only populated when the caller's
        # Authorization header verified as a genuine OIDC token (see
        # CodingModelRouter._get_auth_info) — never re-derive identity from
        # raw, caller-controlled headers here.
        user_id = auth_info.get("user_id") if isinstance(auth_info, dict) else None
        email = auth_info.get("email") if isinstance(auth_info, dict) else None
        user_name = auth_info.get("user_name") if isinstance(auth_info, dict) else None
        auth_provider = (
            auth_info.get("auth_provider") if isinstance(auth_info, dict) else None
        )

        await self.record_usage(
            request_id=request_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            auth_provider=auth_provider,
            email=email,
            user_name=user_name,
        )

    async def record_usage_from_openai_response(
        self,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        response_body: dict[str, Any],
    ) -> None:
        """Extract usage from OpenAI response and record it."""
        usage = response_body.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # auth_info's identity fields are only populated when the caller's
        # Authorization header verified as a genuine OIDC token (see
        # CodingModelRouter._get_auth_info) — never re-derive identity from
        # raw, caller-controlled headers here.
        user_id = auth_info.get("user_id") if isinstance(auth_info, dict) else None
        email = auth_info.get("email") if isinstance(auth_info, dict) else None
        user_name = auth_info.get("user_name") if isinstance(auth_info, dict) else None
        auth_provider = (
            auth_info.get("auth_provider") if isinstance(auth_info, dict) else None
        )

        await self.record_usage(
            request_id=request_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            auth_provider=auth_provider,
            email=email,
            user_name=user_name,
        )

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[usage_tracker] MongoDB connection closed")
