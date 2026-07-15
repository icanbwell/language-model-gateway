"""Usage tracking for model routing - records token usage to MongoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Maps model_tier (the `tier` label in model-router-config.json) to the cost
# bucket used on the per-session rollup document. Ordered roughly by list
# price — "fable" gets its own bucket rather than being folded into one of
# the other three since it's a distinct model family, not a price point
# between them.
_TIER_TO_SESSION_BUCKET: dict[str, str] = {
    "haiku": "low",
    "sonnet": "medium",
    "opus": "high",
    "fable": "fable",
}


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
        session_collection_name: str = "usage_sessions",
        enabled: bool = True,
        track_sessions: bool = True,
        capture_previews: bool = False,
        preview_chars: int = 100,
    ) -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._collection_name = collection_name
        self._session_collection_name = session_collection_name
        self._enabled = enabled
        # Independent of `enabled`: lets the session rollup be turned off (or,
        # eventually, be the only thing turned on) without touching whether
        # per-request tracking happens.
        self._track_sessions = track_sessions
        self._capture_previews = capture_previews
        self._preview_chars = preview_chars
        self._client: Any | None = None
        self._db: Any | None = None
        self._collection: Any | None = None
        self._session_collection: Any | None = None

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
            self._session_collection = self._db[self._session_collection_name]
            logger.info(
                "[usage_tracker] Connected to MongoDB: %s.%s (sessions: %s)",
                self._db_name,
                self._collection_name,
                self._session_collection_name,
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
        start_time: datetime,
        *,
        auth_provider: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
        session_id: str | None = None,
        account_uuid: str | None = None,
        agent_id: str | None = None,
        parent_agent_id: str | None = None,
        model_tier: str | None = None,
        backend: str | None = None,
        bedrock_transport: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        custom_headers: dict[str, str] | None = None,
        sse_event_count: int | None = None,
        retry_count: int | None = None,
        prompt_text: str | None = None,
        response_text: str | None = None,
        raw_usage: dict[str, Any] | None = None,
    ) -> None:
        """Record token usage to MongoDB.

        `bedrock_transport` ("native" or "mantle") disambiguates which
        Bedrock transport handled a `backend="aws_bedrock"` request —
        callers pass it explicitly since, unlike `CodingModelRouter`, this
        class has no `self._bedrock_transport` of its own to derive it from.

        `retry_count` is how many throttle/transient-error retries this
        request needed before it succeeded (0 if none) — see the throttle
        retry loops in `router.py`/`bedrock_native_dispatcher.py`. Passed as
        a plain int (never None) from every dispatch path, including
        Anthropic passthrough, which never retries and always reports 0 —
        so its absence on older records means "not tracked yet", not
        "unknown", and 0 is a meaningful value, not a default standing in
        for missing data.

        `raw_usage` is the upstream response's usage object, stored verbatim
        (whatever shape/keys that upstream uses — Anthropic's
        cache_creation_input_tokens/cache_read_input_tokens, Bedrock
        Converse's cacheReadInputTokens/cacheWriteInputTokens, OpenAI's
        prompt_tokens_details, etc.) so fields this router doesn't yet
        normalize into a top-level column aren't silently dropped.

        `prompt_text`/`response_text` are truncated to `preview_chars`
        (configurable; 0 disables preview capture) before being persisted —
        callers pass the full text and this is the single place that decides
        how much of it is retained.

        `custom_headers` is stored as-is (a flat dict) so new client-supplied
        attribution headers can be added later without a schema change here —
        see CodingModelRouter._get_auth_info for what populates it.

        `start_time` is when the caller received the client's request; it's
        used to derive `end_time`/`duration_ms` — the wall-clock span between
        the request landing and this record being written, which for
        streaming responses is effectively "time to fully respond".
        """
        if input_tokens == 0 and output_tokens == 0:
            return

        await self._ensure_connected()

        if self._collection is None:
            return

        end_time = datetime.now(timezone.utc)
        usage_record: dict[str, Any] = {
            "request_id": request_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "timestamp": end_time,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": round((end_time - start_time).total_seconds() * 1000, 3),
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
        if agent_id:
            usage_record["agent_id"] = agent_id
        if parent_agent_id:
            usage_record["parent_agent_id"] = parent_agent_id
        if model_tier:
            usage_record["model_tier"] = model_tier
        if backend:
            usage_record["backend"] = backend
        if bedrock_transport:
            usage_record["bedrock_transport"] = bedrock_transport
        if price_per_mtok is not None:
            cost_usd = (input_tokens + output_tokens) / 1_000_000 * price_per_mtok
            usage_record["cost_usd"] = round(cost_usd, 6)
            if anthropic_price_per_mtok is not None:
                baseline_cost_usd = (
                    (input_tokens + output_tokens)
                    / 1_000_000
                    * anthropic_price_per_mtok
                )
                usage_record["anthropic_cost_usd"] = round(baseline_cost_usd, 6)
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
        if sse_event_count is not None:
            usage_record["sse_event_count"] = sse_event_count
        if retry_count is not None:
            usage_record["retry_count"] = retry_count
        if raw_usage:
            usage_record["raw_usage"] = raw_usage
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
            return

        if session_id and self._track_sessions:
            try:
                await self._upsert_session_usage(
                    session_id=session_id,
                    account_uuid=account_uuid,
                    user_id=user_id,
                    model=model,
                    model_tier=model_tier,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    price_per_mtok=price_per_mtok,
                    anthropic_price_per_mtok=anthropic_price_per_mtok,
                    retry_count=retry_count,
                )
            except Exception as e:
                logger.warning(
                    "[usage_tracker] Failed to update session usage: %s",
                    e,
                    exc_info=True,
                )

    async def _upsert_session_usage(
        self,
        *,
        session_id: str,
        account_uuid: str | None,
        user_id: str | None,
        model: str,
        model_tier: str | None,
        input_tokens: int,
        output_tokens: int,
        price_per_mtok: float | None,
        anthropic_price_per_mtok: float | None,
        retry_count: int | None = None,
    ) -> None:
        """Roll this request's usage into a single per-session document.

        Keyed by session_id and upserted on every request so a session's
        totals are queryable without a $group aggregation over the (much
        larger) per-request collection. Cost is bucketed by tier — low
        (haiku), medium (sonnet), high (opus), fable — since a single
        session can span multiple model tiers and there's no per-model
        array here (unbounded growth risk for long-running agent sessions).

        Token/cost fields use $inc so concurrent requests in the same
        session (e.g. parallel sub-agent calls) accumulate correctly rather
        than racing on a last-write-wins $set. account_uuid/user_id/tier
        model names are stable per session in practice, so plain $set is
        fine for those.

        `retry_count` rolls into `total_retries`, a session-wide sum (like
        `total_savings_usd`) rather than a per-tier bucket — how many
        retries a session needed overall is the useful signal, not how
        many per tier.
        """
        if self._session_collection is None:
            return

        inc_fields: dict[str, int | float] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
        set_fields: dict[str, str] = {}
        if account_uuid:
            set_fields["account_uuid"] = account_uuid
        if user_id:
            set_fields["user_id"] = user_id

        bucket = _TIER_TO_SESSION_BUCKET.get(model_tier or "")
        cost_usd = anthropic_cost_usd = None
        if price_per_mtok is not None:
            cost_usd = (input_tokens + output_tokens) / 1_000_000 * price_per_mtok
            if anthropic_price_per_mtok is not None:
                anthropic_cost_usd = (
                    (input_tokens + output_tokens)
                    / 1_000_000
                    * anthropic_price_per_mtok
                )
        if bucket:
            if model:
                set_fields[f"{bucket}_tier_model"] = model
            if cost_usd is not None:
                inc_fields[f"{bucket}_tier_cost"] = round(cost_usd, 6)
            if anthropic_cost_usd is not None:
                inc_fields[f"{bucket}_tier_anthropic_cost"] = round(
                    anthropic_cost_usd, 6
                )
        # Savings is a session-wide total, independent of tier bucketing, so
        # it accumulates even for tiers not (yet) mapped to a bucket.
        if cost_usd is not None and anthropic_cost_usd is not None:
            inc_fields["total_savings_usd"] = round(anthropic_cost_usd - cost_usd, 6)
        if retry_count is not None:
            inc_fields["total_retries"] = retry_count

        update: dict[str, dict[str, Any]] = {"$inc": inc_fields}
        if set_fields:
            update["$set"] = set_fields
        await self._session_collection.update_one(
            {"session_id": session_id}, update, upsert=True
        )

    async def record_usage_from_anthropic_response(
        self,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        response_body: dict[str, Any],
        start_time: datetime,
        *,
        model_tier: str | None = None,
        backend: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        prompt_text: str | None = None,
        retry_count: int | None = None,
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
        agent_id = auth_info.get("agent_id") if isinstance(auth_info, dict) else None
        parent_agent_id = (
            auth_info.get("parent_agent_id") if isinstance(auth_info, dict) else None
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
            agent_id=agent_id,
            parent_agent_id=parent_agent_id,
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
            raw_usage=usage,
            start_time=start_time,
            retry_count=retry_count,
        )

    async def record_usage_from_openai_response(
        self,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        response_body: dict[str, Any],
        start_time: datetime,
        *,
        model_tier: str | None = None,
        backend: str | None = None,
        bedrock_transport: str | None = None,
        price_per_mtok: float | None = None,
        anthropic_price_per_mtok: float | None = None,
        streaming: bool | None = None,
        compression_requested: str | None = None,
        compression_used: str | None = None,
        prompt_text: str | None = None,
        retry_count: int | None = None,
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
        agent_id = auth_info.get("agent_id") if isinstance(auth_info, dict) else None
        parent_agent_id = (
            auth_info.get("parent_agent_id") if isinstance(auth_info, dict) else None
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
            agent_id=agent_id,
            parent_agent_id=parent_agent_id,
            model_tier=model_tier,
            backend=backend,
            bedrock_transport=bedrock_transport,
            price_per_mtok=price_per_mtok,
            anthropic_price_per_mtok=anthropic_price_per_mtok,
            streaming=streaming,
            compression_requested=compression_requested,
            compression_used=compression_used,
            custom_headers=custom_headers,
            prompt_text=prompt_text,
            response_text=response_text,
            raw_usage=usage,
            start_time=start_time,
            retry_count=retry_count,
        )

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("[usage_tracker] MongoDB connection closed")
