"""
Streaming adaptation for the native Bedrock Converse API — converts boto3's
synchronous converse_stream() EventStream into an async generator of
Anthropic-format SSE bytes, with an optional usage-tracking wrapper.

Split out of bedrock_converse_client.py, which now owns only client
lifecycle/caching and native-Bedrock error-code classification. Request/
response translation lives in converse_request_translator.py.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Callable

from starlette.requests import Request

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .converse_request_translator import (
    _CONVERSE_TO_ANT_STOP,
    _converse_usage_to_anthropic,
)
from .stream_converter import _fire_and_forget, _sse_event

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))


async def _iter_converse_stream_events(
    sync_events: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Adapt boto3's synchronous converse_stream() EventStream onto the
    asyncio event loop — pulling one event at a time via asyncio.to_thread,
    since boto3 has no native async client and iterating its EventStream
    blocks the thread it's called from.
    """
    iterator = iter(sync_events)

    def _next_event() -> dict[str, Any] | None:
        try:
            result = next(iterator)
            return result  # type: ignore[no-any-return]
        except StopIteration:
            return None

    while True:
        event = await asyncio.to_thread(_next_event)
        if event is None:
            return
        yield event


async def _stream_bedrock_converse_to_anthropic(
    events: AsyncGenerator[dict[str, Any], None],
    msg_id: str,
    upstream_model: str,
    usage_sink: dict[str, Any] | None = None,
    text_sink: dict[str, str] | None = None,
    request: Request | None = None,
    on_stream_error: Callable[[str], None] | None = None,
    tool_name_map: dict[str, str] | None = None,
) -> AsyncGenerator[bytes, None]:
    """Convert a Bedrock Converse event stream to Anthropic SSE format —
    the Converse-API counterpart to
    stream_converter.py:_stream_oai_sdk_to_anthropic. Same external
    contract (sinks, on_stream_error hook, emitted SSE event sequence) so
    it plugs into the existing usage-tracking/cleanup wrapper pattern
    without changes to that pattern itself.

    tool_name_map (from _openai_to_converse_request) restores any tool name
    Bedrock's 64-character limit forced us to shorten before sending.
    """
    if usage_sink is None:
        usage_sink = {}
    usage_sink["input_tokens"] = 0
    usage_sink["output_tokens"] = 0
    usage_sink["cache_creation_input_tokens"] = 0
    usage_sink["cache_read_input_tokens"] = 0
    usage_sink["raw_usage"] = {}
    if text_sink is None:
        text_sink = {}
    text_sink["output_text"] = ""

    yield _sse_event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": upstream_model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 1},
            },
        },
    )
    yield _sse_event("ping", {"type": "ping"})

    open_block_types: dict[int, str] = {}
    any_block_opened = False
    stop_reason = "end_turn"
    stream_error_msg: str | None = None

    try:
        async for event in events:
            if request is not None and await request.is_disconnected():
                logger.info(
                    "[bedrock-converse] request_id=%s client disconnected "
                    "mid-stream — stopping upstream consumption",
                    msg_id,
                )
                break
            if "contentBlockStart" in event:
                any_block_opened = True
                idx = event["contentBlockStart"]["contentBlockIndex"]
                start = event["contentBlockStart"].get("start") or {}
                if "toolUse" in start:
                    tool_use = start["toolUse"]
                    safe_name = tool_use.get("name", "")
                    open_block_types[idx] = "tool_use"
                    yield _sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": idx,
                            "content_block": {
                                "type": "tool_use",
                                "id": tool_use.get("toolUseId", ""),
                                "name": (tool_name_map or {}).get(safe_name, safe_name),
                                "input": {},
                            },
                        },
                    )
                else:
                    open_block_types[idx] = "text"
                    yield _sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": idx,
                            "content_block": {"type": "text", "text": ""},
                        },
                    )
            elif "contentBlockDelta" in event:
                idx = event["contentBlockDelta"]["contentBlockIndex"]
                delta = event["contentBlockDelta"]["delta"]
                if idx not in open_block_types:
                    # Some Bedrock Converse backends (observed with
                    # qwen.qwen3-coder-next over the native transport) skip
                    # contentBlockStart and go straight to contentBlockDelta.
                    # Forwarding the delta without ever having sent a start
                    # for this index breaks Claude Code's SSE parser
                    # ("Content block not found") — lazily open it here so
                    # the client-facing stream stays well-formed.
                    any_block_opened = True
                    block_type = "tool_use" if "toolUse" in delta else "text"
                    open_block_types[idx] = block_type
                    yield _sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": idx,
                            "content_block": (
                                {
                                    "type": "tool_use",
                                    "id": "",
                                    "name": "",
                                    "input": {},
                                }
                                if block_type == "tool_use"
                                else {"type": "text", "text": ""}
                            ),
                        },
                    )
                if "text" in delta:
                    text_sink["output_text"] += delta["text"]
                    yield _sse_event(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": idx,
                            "delta": {"type": "text_delta", "text": delta["text"]},
                        },
                    )
                elif "toolUse" in delta:
                    yield _sse_event(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": idx,
                            "delta": {
                                "type": "input_json_delta",
                                "partial_json": delta["toolUse"].get("input", ""),
                            },
                        },
                    )
            elif "contentBlockStop" in event:
                idx = event["contentBlockStop"]["contentBlockIndex"]
                open_block_types.pop(idx, None)
                yield _sse_event(
                    "content_block_stop", {"type": "content_block_stop", "index": idx}
                )
            elif "messageStop" in event:
                stop_reason = _CONVERSE_TO_ANT_STOP.get(
                    event["messageStop"].get("stopReason", ""), "end_turn"
                )
            elif "metadata" in event:
                usage = event["metadata"].get("usage", {})
                usage_sink["raw_usage"] = usage
                anthropic_usage = _converse_usage_to_anthropic(usage)
                usage_sink["input_tokens"] = anthropic_usage["input_tokens"]
                usage_sink["output_tokens"] = anthropic_usage["output_tokens"]
                usage_sink["cache_creation_input_tokens"] = anthropic_usage[
                    "cache_creation_input_tokens"
                ]
                usage_sink["cache_read_input_tokens"] = anthropic_usage[
                    "cache_read_input_tokens"
                ]
    except Exception as exc:
        logger.error("[bedrock-converse] upstream stream error: %s", exc)
        stream_error_msg = str(exc)
        if on_stream_error is not None:
            on_stream_error(stream_error_msg)

    for idx in sorted(open_block_types):
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": idx}
        )

    # message_start is emitted eagerly at the top of this function (unlike
    # Mantle's lazy gate in _stream_oai_sdk_to_anthropic), so an error that
    # arrives before the first content block would otherwise produce a
    # silently empty, well-formed assistant message — the client never sees
    # that anything went wrong, even though the failure IS recorded via
    # on_stream_error above. Mirror Mantle's inline-error-text injection here,
    # gated on "no content block has ever been opened" (not just "no blocks
    # are currently open" — a block could have opened AND closed before the
    # error hit).
    if stream_error_msg and not any_block_opened:
        yield _sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        )
        yield _sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": f"[bedrock-native-proxy error] {stream_error_msg}",
                },
            },
        )
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": 0}
        )

    if not any_block_opened and not stream_error_msg:
        # No error, but the model produced no visible content at all (e.g.
        # it exhausted its token budget entirely within reasoning/thinking
        # that never surfaced as a content block). A message with
        # content=[] isn't valid Anthropic protocol and breaks Claude
        # Code's SSE parser, so guarantee at least one (empty) block.
        yield _sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        )
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": 0}
        )

    yield _sse_event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {
                "output_tokens": usage_sink["output_tokens"],
                "cache_creation_input_tokens": usage_sink[
                    "cache_creation_input_tokens"
                ],
                "cache_read_input_tokens": usage_sink["cache_read_input_tokens"],
            },
        },
    )
    yield _sse_event("message_stop", {"type": "message_stop"})


async def _converse_stream_with_usage_tracking(
    events: AsyncGenerator[dict[str, Any], None],
    msg_id: str,
    upstream_model: str,
    usage_tracker: Any,
    auth_info: dict[str, Any],
    start_time: datetime,
    *,
    prompt_text: str | None = None,
    model_tier: str | None = None,
    backend: str | None = None,
    price_per_mtok: float | None = None,
    anthropic_price_per_mtok: float | None = None,
    compression_requested: str | None = None,
    compression_used: str | None = None,
    request: Request | None = None,
    on_stream_error: Callable[[str], None] | None = None,
    tool_name_map: dict[str, str] | None = None,
) -> AsyncGenerator[bytes, None]:
    """Stream wrapper that records usage to MongoDB after the stream
    completes — the Converse-API counterpart to
    stream_converter.py:_oai_stream_with_usage_tracking. No httpx client to
    close here (boto3 manages its own connection pooling internally), so
    this is simpler than its OAI counterpart — just the sink bookkeeping
    and the record_usage call.
    """
    usage_sink: dict[str, Any] = {}
    text_sink: dict[str, str] = {}
    async for chunk in _stream_bedrock_converse_to_anthropic(
        events,
        msg_id,
        upstream_model,
        usage_sink=usage_sink,
        text_sink=text_sink,
        request=request,
        on_stream_error=on_stream_error,
        tool_name_map=tool_name_map,
    ):
        yield chunk

    input_tokens = usage_sink.get("input_tokens", 0)
    output_tokens = usage_sink.get("output_tokens", 0)
    if usage_tracker and (input_tokens > 0 or output_tokens > 0):
        _fire_and_forget(
            usage_tracker.record_usage(
                request_id=msg_id,
                user_id=auth_info.get("user_id"),
                model=upstream_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                auth_provider=auth_info.get("auth_provider"),
                email=auth_info.get("email"),
                user_name=auth_info.get("user_name"),
                session_id=auth_info.get("session_id"),
                account_uuid=auth_info.get("account_uuid"),
                agent_id=auth_info.get("agent_id"),
                parent_agent_id=auth_info.get("parent_agent_id"),
                model_tier=model_tier,
                backend=backend,
                # This is the Converse-API streaming path — always native,
                # unlike Mantle's counterpart which threads the value in
                # from the caller's self._bedrock_transport.
                bedrock_transport="native",
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                streaming=True,
                compression_requested=compression_requested,
                compression_used=compression_used,
                custom_headers=auth_info.get("custom_headers"),
                prompt_text=prompt_text,
                response_text=text_sink.get("output_text"),
                raw_usage=usage_sink.get("raw_usage"),
                start_time=start_time,
            )
        )
