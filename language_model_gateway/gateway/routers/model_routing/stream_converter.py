from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
from typing import Any, AsyncGenerator, Coroutine

import httpx

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .constants import _OAI_TO_ANT_STOP

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

# asyncio does not keep a strong reference to a bare create_task() result, so an
# in-flight task can be garbage-collected before it finishes. Stash a reference here
# until the task's own done-callback removes it.
_background_tasks: set[asyncio.Task[Any]] = set()


def _fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


class ThinkingStripper:
    """Strip <think>…</think> blocks from streamed Bedrock OpenAI output."""

    _OPEN = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._buf = ""
        self._inside = False

    def feed(self, text: str) -> str:
        self._buf += text
        out: list[str] = []
        while True:
            if self._inside:
                end = self._buf.find(self._CLOSE)
                if end == -1:
                    # Discard content inside the think block; keep only a suffix that
                    # could be the start of the close tag so it isn't lost across chunks.
                    safe = self._safe_forward_len_close()
                    self._buf = self._buf[safe:]
                    break
                self._inside = False
                self._buf = self._buf[end + len(self._CLOSE) :]
                if self._buf.startswith("\n"):
                    self._buf = self._buf[1:]
            else:
                start = self._buf.find(self._OPEN)
                if start == -1:
                    safe = self._safe_forward_len()
                    out.append(self._buf[:safe])
                    self._buf = self._buf[safe:]
                    break
                out.append(self._buf[:start])
                self._inside = True
                self._buf = self._buf[start + len(self._OPEN) :]
        return "".join(out)

    def flush(self) -> str:
        if self._inside:
            self._buf = ""
            self._inside = False
            return ""
        result, self._buf = self._buf, ""
        return result

    def _safe_forward_len(self) -> int:
        tag = self._OPEN
        for i in range(1, len(tag)):
            if self._buf.endswith(tag[:i]):
                return len(self._buf) - i
        return len(self._buf)

    def _safe_forward_len_close(self) -> int:
        """Return length to preserve trailing suffix that could be prefix of _CLOSE."""
        tag = self._CLOSE
        for i in range(1, len(tag)):
            if self._buf.endswith(tag[:i]):
                return len(self._buf) - i
        return len(self._buf)


def _msg_id() -> str:
    return "msg_" + os.urandom(12).hex()


def _sse_event(event_type: str, data: dict[str, Any]) -> bytes:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()


async def _stream_oai_sdk_to_anthropic(
    stream: Any,
    msg_id: str,
    upstream_model: str,
    first_chunk: Any = None,
    usage_sink: dict[str, int] | None = None,
    text_sink: dict[str, str] | None = None,
) -> AsyncGenerator[bytes, None]:
    """Convert an openai SDK async stream to Anthropic SSE format.

    Accumulated input/output token usage is written into `usage_sink` (if
    provided), and the visible output text into `text_sink` (if provided),
    so callers can read them after the stream completes without relying on
    shared module state across concurrent requests.
    """
    if usage_sink is None:
        usage_sink = {}
    usage_sink["input_tokens"] = 0
    usage_sink["output_tokens"] = 0
    if text_sink is None:
        text_sink = {}
    text_sink["output_text"] = ""

    sent_message_start = False
    open_blocks: dict[int, dict[str, Any]] = {}
    next_idx = 0
    text_idx: int | None = None
    tool_idx_map: dict[int, int] = {}
    finish_reason: str | None = None
    output_tokens = 0
    thinking_stripper = ThinkingStripper()

    async def _iter_stream() -> AsyncGenerator[Any, None]:
        if first_chunk is not None:
            yield first_chunk
        async for chunk in stream:
            yield chunk

    try:
        async for chunk in _iter_stream():
            if not sent_message_start:
                sent_message_start = True
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

            for choice in chunk.choices:
                delta = choice.delta
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                if delta.content:
                    visible = thinking_stripper.feed(delta.content)
                    if visible:
                        text_sink["output_text"] += visible
                        if text_idx is None:
                            text_idx = next_idx
                            next_idx += 1
                            open_blocks[text_idx] = {"type": "text"}
                            yield _sse_event(
                                "content_block_start",
                                {
                                    "type": "content_block_start",
                                    "index": text_idx,
                                    "content_block": {"type": "text", "text": ""},
                                },
                            )
                        yield _sse_event(
                            "content_block_delta",
                            {
                                "type": "content_block_delta",
                                "index": text_idx,
                                "delta": {"type": "text_delta", "text": visible},
                            },
                        )
                for tc in delta.tool_calls or []:
                    oai_tc_idx = tc.index
                    if oai_tc_idx not in tool_idx_map:
                        ant_idx = next_idx
                        next_idx += 1
                        tool_idx_map[oai_tc_idx] = ant_idx
                        tc_id = tc.id or f"toolu_{ant_idx:04x}"
                        tc_name = (tc.function.name if tc.function else "") or ""
                        open_blocks[ant_idx] = {"type": "tool_use"}
                        yield _sse_event(
                            "content_block_start",
                            {
                                "type": "content_block_start",
                                "index": ant_idx,
                                "content_block": {
                                    "type": "tool_use",
                                    "id": tc_id,
                                    "name": tc_name,
                                    "input": {},
                                },
                            },
                        )
                    ant_idx = tool_idx_map[oai_tc_idx]
                    if tc.function and tc.function.arguments:
                        yield _sse_event(
                            "content_block_delta",
                            {
                                "type": "content_block_delta",
                                "index": ant_idx,
                                "delta": {
                                    "type": "input_json_delta",
                                    "partial_json": tc.function.arguments,
                                },
                            },
                        )
            if chunk.usage:
                # Capture both input and output tokens from usage
                if chunk.usage.prompt_tokens is not None:
                    usage_sink["input_tokens"] = chunk.usage.prompt_tokens
                if chunk.usage.completion_tokens is not None:
                    usage_sink["output_tokens"] = chunk.usage.completion_tokens
    except Exception as _exc:
        logger.error("[coding-model-router] upstream stream error: %s", _exc)
        _stream_error_msg: str | None = str(_exc)
    else:
        _stream_error_msg = None
    finally:
        if stream is not None:
            # Handle both sync close() and async aclose()
            close_method = getattr(stream, "aclose", getattr(stream, "close", None))
            if close_method is not None:
                _close_result = close_method()
                if inspect.isawaitable(_close_result):
                    await _close_result

    if not sent_message_start:
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
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                },
            },
        )
        yield _sse_event("ping", {"type": "ping"})

    if _stream_error_msg and not sent_message_start:
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
                    "text": f"[anthropic-proxy error] {_stream_error_msg}",
                },
            },
        )
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": 0}
        )

    remaining = thinking_stripper.flush()
    if remaining:
        text_sink["output_text"] += remaining
        if text_idx is None:
            text_idx = next_idx
            next_idx += 1
            open_blocks[text_idx] = {"type": "text"}
            yield _sse_event(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": text_idx,
                    "content_block": {"type": "text", "text": ""},
                },
            )
        yield _sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": text_idx,
                "delta": {"type": "text_delta", "text": remaining},
            },
        )

    for idx in sorted(open_blocks):
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": idx}
        )

    stop_reason = _OAI_TO_ANT_STOP.get(finish_reason or "stop", "end_turn")
    yield _sse_event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        },
    )
    yield _sse_event("message_stop", {"type": "message_stop"})


async def _oai_stream_with_cleanup(
    stream: Any,
    msg_id: str,
    upstream_model: str,
    http_client: httpx.AsyncClient,
    first_chunk: Any = None,
) -> AsyncGenerator[bytes, None]:
    """
    Stream wrapper that closes the upstream HTTP client after the stream
    completes. Does not record usage.
    """
    try:
        async for chunk in _stream_oai_sdk_to_anthropic(
            stream, msg_id, upstream_model, first_chunk=first_chunk
        ):
            yield chunk
    finally:
        await http_client.aclose()


async def _oai_stream_with_usage_tracking(
    stream: Any,
    msg_id: str,
    upstream_model: str,
    http_client: httpx.AsyncClient,
    usage_tracker: Any,
    auth_info: dict[str, Any],
    first_chunk: Any = None,
    prompt_text: str | None = None,
) -> AsyncGenerator[bytes, None]:
    """
    Stream wrapper that records usage to MongoDB after stream completes.
    """
    usage_sink: dict[str, int] = {}
    text_sink: dict[str, str] = {}
    try:
        async for chunk in _stream_oai_sdk_to_anthropic(
            stream,
            msg_id,
            upstream_model,
            first_chunk=first_chunk,
            usage_sink=usage_sink,
            text_sink=text_sink,
        ):
            yield chunk
    finally:
        await http_client.aclose()
        input_tokens = usage_sink.get("input_tokens", 0)
        output_tokens = usage_sink.get("output_tokens", 0)
        if usage_tracker and (input_tokens > 0 or output_tokens > 0):
            # Fire-and-forget: don't hold the stream's close on the Mongo write.
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
                    prompt_text=prompt_text,
                    response_text=text_sink.get("output_text"),
                )
            )


async def _stream_passthrough(
    resp: httpx.Response,
    client: httpx.AsyncClient,
) -> AsyncGenerator[bytes, None]:
    try:
        async for chunk in resp.aiter_bytes():
            yield chunk
    finally:
        await resp.aclose()
        await client.aclose()
