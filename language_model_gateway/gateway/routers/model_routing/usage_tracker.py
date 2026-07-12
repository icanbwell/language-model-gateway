"""Usage tracking for model routing - records token usage to MongoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _truncate(text: str | None, limit: int) -> str | None:
    """Truncate to `limit` chars, marking truncation with a trailing "…".

    The marker makes it unambiguous when eyeballing a usage record whether
    input_preview/output_preview is the whole text or a cut-off prefix.
    """
    if not text or limit <= 0:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


class UsageTracker:
    """Tracks and records token usage to MongoDB for model routing."""

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "llm_storage",
        collection_name: str = "usage",
        enabled: bool = True,
        capture_previews: bool = False,
        preview_chars: int = 100,
    ) -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._collection_name = collection_name
        self._enabled = enabled
        self._capture_previews = capture_previews
        self._preview_chars = preview_chars
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
        session_id: str | None = None,
        account_uuid: str | None = None,
        model_tier: str | None = None,
        backend: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        custom_headers: dict[str, str] | None = None,
        prompt_text: str | None = None,
        response_text: str | None = None,
    ) -> None:
        """Record token usage to MongoDB.

        `prompt_text`/`response_text` are truncated to `preview_chars`
        (configurable; 0 disables preview capture) before being persisted —
        callers pass the full text and this is the single place that decides
        how much of it is retained.

        `custom_headers` is stored as-is (a flat dict) so new client-supplied
        attribution headers can be added later without a schema change here —
        see CodingModelRouter._get_auth_info for what populates it.
        """
        if input_tokens == 0 and output_tokens == 0:
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
            "timestamp": datetime.now(timezone.utc),
        }

        if user_id:
            usage_record["user_id"] = user_id
        if auth_provider:
            usage_record["auth_provider"] = auth_provider
        if email:
            usage_record["email"] = email
        if user_name:
            usage_record["user_name"] = user_name
        if session_id:
            usage_record["session_id"] = session_id
        if account_uuid:
            usage_record["account_uuid"] = account_uuid
        if model_tier:
            usage_record["model_tier"] = model_tier
        if backend:
            usage_record["backend"] = backend
        if price_per_mtok is not None:
            cost_usd = (input_tokens + output_tokens) / 1_000_000 * price_per_mtok
            usage_record["cost_usd"] = round(cost_usd, 6)
            if anthropic_price_per_mtok is not None:
                baseline_cost_usd = (
                    (input_tokens + output_tokens)
                    / 1_000_000
                    * anthropic_price_per_mtok
                )
                usage_record["cost_savings_usd"] = round(
                    baseline_cost_usd - cost_usd, 6
                )
        if streaming is not None:
            usage_record["streaming"] = streaming
        if compression_requested:
            usage_record["compression_requested"] = compression_requested
        if compression_used:
            usage_record["compression_used"] = compression_used
        if custom_headers:
            usage_record["custom_headers"] = custom_headers
        if self._capture_previews:
            if input_preview := _truncate(prompt_text, self._preview_chars):
                usage_record["input_preview"] = input_preview
            if output_preview := _truncate(response_text, self._preview_chars):
                usage_record["output_preview"] = output_preview

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
        model_tier: str | None = None,
        backend: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        prompt_text: str | None = None,
    ) -> None:
        """Extract usage from Anthropic response and record it."""
        custom_headers = (
            auth_info.get("custom_headers") if isinstance(auth_info, dict) else None
        )
        usage = response_body.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # auth_info's identity fields are only populated when the caller's
        # Authorization header verified as a genuine OIDC token (see
        # CodingModelRouter._get_auth_info) — never re-derive identity from
        # raw, caller-controlled headers here. session_id is not an identity
        # field (see extract_session_id) so it's trusted regardless.
        user_id = auth_info.get("user_id") if isinstance(auth_info, dict) else None
        email = auth_info.get("email") if isinstance(auth_info, dict) else None
        user_name = auth_info.get("user_name") if isinstance(auth_info, dict) else None
        auth_provider = (
            auth_info.get("auth_provider") if isinstance(auth_info, dict) else None
        )
        session_id = (
            auth_info.get("session_id") if isinstance(auth_info, dict) else None
        )
        account_uuid = (
            auth_info.get("account_uuid") if isinstance(auth_info, dict) else None
        )

        content_blocks = response_body.get("content")
        response_text = None
        if isinstance(content_blocks, list):
            texts = [
                text
                for block in content_blocks
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(text := block.get("text"), str)
            ]
            response_text = "\n".join(texts) if texts else None

        await self.record_usage(
            request_id=request_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            auth_provider=auth_provider,
            email=email,
            user_name=user_name,
            session_id=session_id,
            account_uuid=account_uuid,
            model_tier=model_tier,
            backend=backend,
            price_per_mtok=price_per_mtok,
            anthropic_price_per_mtok=anthropic_price_per_mtok,
            streaming=streaming,
            compression_requested=compression_requested,
            compression_used=compression_used,
            custom_headers=custom_headers,
            prompt_text=prompt_text,
            response_text=response_text,
        )

    async def record_usage_from_openai_response(
        self,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        response_body: dict[str, Any],
        model_tier: str | None = None,
        backend: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        prompt_text: str | None = None,
    ) -> None:
        """Extract usage from OpenAI response and record it."""
        custom_headers = (
            auth_info.get("custom_headers") if isinstance(auth_info, dict) else None
        )
        usage = response_body.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # auth_info's identity fields are only populated when the caller's
        # Authorization header verified as a genuine OIDC token (see
        # CodingModelRouter._get_auth_info) — never re-derive identity from
        # raw, caller-controlled headers here. session_id is not an identity
        # field (see extract_session_id) so it's trusted regardless.
        user_id = auth_info.get("user_id") if isinstance(auth_info, dict) else None
        email = auth_info.get("email") if isinstance(auth_info, dict) else None
        user_name = auth_info.get("user_name") if isinstance(auth_info, dict) else None
        auth_provider = (
            auth_info.get("auth_provider") if isinstance(auth_info, dict) else None
        )
        session_id = (
            auth_info.get("session_id") if isinstance(auth_info, dict) else None
        )
        account_uuid = (
            auth_info.get("account_uuid") if isinstance(auth_info, dict) else None
        )

        choices = response_body.get("choices")
        response_text = None
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            message = (
                first_choice.get("message") if isinstance(first_choice, dict) else None
            )
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                response_text = message["content"]

        await self.record_usage(
            request_id=request_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            auth_provider=auth_provider,
            email=email,
            user_name=user_name,
            session_id=session_id,
            account_uuid=account_uuid,
            model_tier=model_tier,
            backend=backend,
            price_per_mtok=price_per_mtok,
            anthropic_price_per_mtok=anthropic_price_per_mtok,
            streaming=streaming,
            compression_requested=compression_requested,
            compression_used=compression_used,
            custom_headers=custom_headers,
            prompt_text=prompt_text,
            response_text=response_text,
        )

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[usage_tracker] MongoDB connection closed")
