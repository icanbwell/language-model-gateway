"""
CodingModelRouter — Anthropic Messages API proxy route.

Routes requests to either Anthropic direct (passthrough) or AWS Bedrock based on a
JSON config keyed by model name. No local model support.

Route config is loaded from the path in the ROUTER_CONFIG environment variable
(default: ~/model-router/router_config.json), using the same schema as
coding-model-router/router.py.

Supported auth strategies:
  passthrough  → Anthropic API direct; client Authorization header forwarded as-is.
  aws          → AWS Bedrock; SigV4-signed per request.

Supported wire protocols (route.api_type, default "anthropic"):
  anthropic    → Upstream speaks Anthropic Messages API; bytes forwarded verbatim.
  openai       → Upstream speaks OpenAI Chat Completions API (Bedrock Mantle);
                 request translated from Anthropic format, response translated back.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Sequence, override

import httpx
from fastapi import APIRouter
from fastapi import params
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(
    os.environ.get("ROUTER_CONFIG", Path.home() / "model-router" / "router_config.json")
)


def _load_config() -> dict[str, Any]:
    try:
        with open(_CONFIG_PATH) as f:
            result: dict[str, Any] = json.load(f)
            return result
    except FileNotFoundError:
        logger.warning(
            "[coding-model-router] config not found at %s — no routes configured; "
            "unknown models fall back to Anthropic direct",
            _CONFIG_PATH,
        )
        return {"routes": []}


_CONFIG: dict[str, Any] = _load_config()
_ROUTES: dict[str, dict[str, Any]] = {}
for _r in _CONFIG.get("routes", []):
    _key = _r["claude_model"]
    if _key in _ROUTES:
        logger.warning(
            "[coding-model-router] duplicate route for model '%s' — later entry wins",
            _key,
        )
    _ROUTES[_key] = _r


def _find_route(model: str) -> dict[str, Any] | None:
    return _ROUTES.get(model)


# ---------------------------------------------------------------------------
# SigV4 signing for Bedrock
# ---------------------------------------------------------------------------


def _sign_bedrock(url: str, body: bytes, route: dict[str, Any]) -> dict[str, str]:
    """Return headers dict with AWS SigV4 Authorization for a Bedrock POST."""
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    profile = os.environ.get("AWS_PROFILE")
    region = route.get("aws_region", "us-east-1")
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    raw_creds = session.get_credentials()
    if raw_creds is None:
        raise RuntimeError("No AWS credentials available")
    creds = raw_creds.get_frozen_credentials()
    req = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(creds, "bedrock", region).add_auth(req)
    return dict(req.headers)


class _SigV4Auth(httpx.Auth):
    """Apply AWS SigV4 signing per request via httpx.Auth (used by openai SDK transport)."""

    def __init__(self, route: dict[str, Any]) -> None:
        self._route = route

    @override
    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        signed = _sign_bedrock(str(request.url), request.content, self._route)
        for k, v in signed.items():
            request.headers[k.lower()] = v
        yield request


# ---------------------------------------------------------------------------
# Bedrock throttle retry / dispatch pacing
# ---------------------------------------------------------------------------

_BEDROCK_MIN_DISPATCH_INTERVAL_S = 0.3
_bedrock_dispatch_lock = asyncio.Lock()
_bedrock_last_dispatch: float = 0.0

_MAX_THROTTLE_RETRIES = 5
_THROTTLE_BASE_DELAY_S = 1.0
_THROTTLE_MAX_DELAY_S = 20.0

_THROTTLE_TEXT_RE = re.compile(
    r"throttl|too many requests|rate.?limit|try again later"
    r"|increase.*traffic|traffic.*increase"
    r"|on.?demand.capacity|exceed.*capacity|double faster",
    re.IGNORECASE,
)
_CONTEXT_OVERFLOW_RE = re.compile(
    r"contains at least (\d+) input tokens", re.IGNORECASE
)


async def _pace_bedrock_dispatch() -> None:
    global _bedrock_last_dispatch
    async with _bedrock_dispatch_lock:
        loop = asyncio.get_running_loop()
        wait = _BEDROCK_MIN_DISPATCH_INTERVAL_S - (loop.time() - _bedrock_last_dispatch)
        if wait > 0:
            await asyncio.sleep(wait)
        _bedrock_last_dispatch = asyncio.get_running_loop().time()


def _throttle_backoff(attempt: int) -> float:
    ceiling = min(_THROTTLE_MAX_DELAY_S, _THROTTLE_BASE_DELAY_S * (2**attempt))
    return random.uniform(ceiling / 2, ceiling)


def _is_throttling(status_code: int, body_text: str = "") -> bool:
    if _CONTEXT_OVERFLOW_RE.search(body_text or ""):
        return False
    if status_code == 429:
        return True
    if status_code >= 400 and _THROTTLE_TEXT_RE.search(body_text or ""):
        return True
    return False


async def _send_with_bedrock_retry(
    client: httpx.AsyncClient,
    target_url: str,
    upstream_headers: dict[str, str],
    raw_body: bytes,
    route: dict[str, Any],
    auth: str,
) -> httpx.Response:
    attempt = 0
    while True:
        if auth == "aws":
            await _pace_bedrock_dispatch()
        upstream_req = client.build_request(
            "POST", target_url, headers=upstream_headers, content=raw_body
        )
        resp = await client.send(upstream_req, stream=True)

        if auth != "aws" or resp.status_code < 400 or attempt >= _MAX_THROTTLE_RETRIES:
            return resp

        error_body = await resp.aread()
        await resp.aclose()
        error_text = error_body.decode("utf-8", errors="replace")

        if not _is_throttling(resp.status_code, error_text):
            return httpx.Response(
                status_code=resp.status_code, headers=resp.headers, content=error_body
            )

        delay = _throttle_backoff(attempt)
        attempt += 1
        logger.warning(
            "[coding-model-router] Bedrock throttled (attempt %d/%d): backing off %.1fs — %s",
            attempt,
            _MAX_THROTTLE_RETRIES,
            delay,
            error_text[:200],
        )
        await asyncio.sleep(delay)
        sig_headers = {
            k.lower(): v for k, v in _sign_bedrock(target_url, raw_body, route).items()
        }
        upstream_headers = {**upstream_headers, **sig_headers}


# ---------------------------------------------------------------------------
# OpenAI <-> Anthropic translation (for api_type="openai" Bedrock routes)
# ---------------------------------------------------------------------------

_OAI_TO_ANT_STOP = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}
_ANTHROPIC_ONLY_HEADERS = frozenset(
    {"anthropic-version", "anthropic-beta", "x-api-key"}
)


class _ThinkingStripper:
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
                    self._buf = ""
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


def _msg_id() -> str:
    return "msg_" + os.urandom(12).hex()


def _sse_event(event_type: str, data: dict[str, Any]) -> bytes:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()


def _anthropic_content_to_text(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text")


def _convert_user_content(blocks: list[Any]) -> str | list[Any]:
    text_only = all(b.get("type") == "text" for b in blocks)
    if text_only:
        return "\n".join(b.get("text", "") for b in blocks)
    result = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            result.append({"type": "text", "text": block.get("text", "")})
        elif btype == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                url = f"data:{src.get('media_type', 'image/jpeg')};base64,{src.get('data', '')}"
            else:
                url = src.get("url", "")
            result.append({"type": "image_url", "image_url": {"url": url}})
    return result


def _anthropic_to_openai_request(body_json: dict[str, Any]) -> dict[str, Any]:
    """Translate an Anthropic Messages API request body to OpenAI Chat Completions format."""
    oai: dict[str, Any] = {"model": body_json["model"]}
    for field in ("stream", "temperature", "top_p", "max_tokens"):
        if field in body_json:
            oai[field] = body_json[field]

    messages: list[Any] = []
    if system := body_json.get("system"):
        messages.append(
            {"role": "system", "content": _anthropic_content_to_text(system)}
        )

    for msg in body_json.get("messages", []):
        role = msg["role"]
        content = msg["content"]
        if role == "assistant":
            if isinstance(content, list):
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for block in content:
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(block.get("text", ""))
                    elif btype == "tool_use":
                        tool_calls.append(
                            {
                                "id": block.get("id", f"call_{len(tool_calls)}"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            }
                        )
                oai_msg: dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    oai_msg["content"] = "\n".join(text_parts)
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                messages.append(oai_msg)
            else:
                messages.append({"role": "assistant", "content": content or ""})
        elif role == "user":
            if isinstance(content, list):
                pending: list[Any] = []
                for block in content:
                    if block.get("type") == "tool_result":
                        if pending:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": _convert_user_content(pending),
                                }
                            )
                            pending = []
                        result_content = block.get("content", "")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "content": (
                                    _anthropic_content_to_text(result_content)
                                    if isinstance(result_content, list)
                                    else str(result_content or "")
                                ),
                            }
                        )
                    else:
                        pending.append(block)
                if pending:
                    messages.append(
                        {"role": "user", "content": _convert_user_content(pending)}
                    )
            else:
                messages.append({"role": "user", "content": content or ""})

    oai["messages"] = messages

    if tools := body_json.get("tools"):
        oai["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in tools
        ]

    if tc := body_json.get("tool_choice"):
        tc_type = tc.get("type")
        if tc_type == "auto":
            oai["tool_choice"] = "auto"
        elif tc_type == "any":
            oai["tool_choice"] = "required"
        elif tc_type == "none":
            oai["tool_choice"] = "none"
        elif tc_type == "tool":
            oai["tool_choice"] = {
                "type": "function",
                "function": {"name": tc.get("name", "")},
            }

    return oai


def _openai_to_anthropic_response(
    resp_json: dict[str, Any], msg_id: str, upstream_model: str
) -> dict[str, Any]:
    """Translate a non-streaming OpenAI Chat Completions response to Anthropic format."""
    usage = resp_json.get("usage", {})
    content: list[Any] = []
    stop_reason = "end_turn"
    choices = resp_json.get("choices", [])
    if choices:
        choice = choices[0]
        message = choice.get("message", {})
        stop_reason = _OAI_TO_ANT_STOP.get(
            choice.get("finish_reason", "stop"), "end_turn"
        )
        if text := message.get("content"):
            text = (
                re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
                .strip("\n")
                .strip()
            )
            if text:
                content.append({"type": "text", "text": text})
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                input_data = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                input_data = {}
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.get("id", f"toolu_{len(content):04x}"),
                    "name": fn.get("name", ""),
                    "input": input_data,
                }
            )
    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": upstream_model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


async def _stream_oai_sdk_to_anthropic(
    stream: Any,
    msg_id: str,
    upstream_model: str,
    first_chunk: Any = None,
) -> AsyncGenerator[bytes, None]:
    """Convert an openai SDK async stream to Anthropic SSE format."""
    sent_message_start = False
    open_blocks: dict[int, dict[str, Any]] = {}
    next_idx = 0
    text_idx: int | None = None
    tool_idx_map: dict[int, int] = {}
    finish_reason: str | None = None
    output_tokens = 0
    thinking_stripper = _ThinkingStripper()

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
            if chunk.usage and chunk.usage.completion_tokens is not None:
                output_tokens = chunk.usage.completion_tokens
    except Exception as _exc:
        logger.error("[coding-model-router] upstream stream error: %s", _exc)
        _stream_error_msg: str | None = str(_exc)
    else:
        _stream_error_msg = None
    finally:
        await stream.close()

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
    try:
        async for chunk in _stream_oai_sdk_to_anthropic(
            stream, msg_id, upstream_model, first_chunk=first_chunk
        ):
            yield chunk
    finally:
        await http_client.aclose()


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


# ---------------------------------------------------------------------------
# Router class
# ---------------------------------------------------------------------------

_SKIP_HEADERS = frozenset(
    {"host", "content-length", "transfer-encoding", "authorization"}
)


class CodingModelRouter:
    """
    Proxies Anthropic Messages API requests to Anthropic direct or AWS Bedrock.

    Reads route config from ROUTER_CONFIG env var (same schema as coding-model-router).
    Supports auth=passthrough (Anthropic) and auth=aws (Bedrock). No local model support.
    """

    def __init__(
        self,
        *,
        prefix: str = "/v1",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        self.router = APIRouter(
            prefix=prefix,
            tags=tags or ["anthropic-proxy"],
            dependencies=dependencies or [],
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/messages",
            self.proxy_messages,
            methods=["POST"],
            response_model=None,
            summary="Proxy Anthropic Messages API",
            description="Routes to Anthropic direct or AWS Bedrock based on model name.",
            status_code=200,
        )
        self.router.add_api_route(
            "/messages/count_tokens",
            self.proxy_messages,
            methods=["POST"],
            response_model=None,
            summary="Proxy Anthropic token count endpoint",
            status_code=200,
        )

    async def proxy_messages(
        self, request: Request
    ) -> StreamingResponse | JSONResponse | Response:
        raw_body = await request.body()
        try:
            body_json = json.loads(raw_body)
        except json.JSONDecodeError:
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)

        model: str = body_json.get("model", "")
        route = _find_route(model)
        req_suffix = request.url.path[len("/v1/messages") :]

        if route is None:
            logger.warning(
                "[coding-model-router] unknown model '%s' — falling back to Anthropic direct",
                model,
            )
            route = {
                "auth": "passthrough",
                "url": f"https://api.anthropic.com/v1/messages{req_suffix}",
                "model": model,
            }

        auth: str = route["auth"]
        api_type: str = route.get("api_type", "anthropic")
        upstream_model: str = route["model"]
        is_streaming: bool = bool(body_json.get("stream"))

        # OpenAI-format Bedrock endpoints don't support /count_tokens — return estimate
        if req_suffix == "/count_tokens" and api_type == "openai":
            return JSONResponse({"input_tokens": len(json.dumps(body_json)) // 4})

        target_url = route["url"] if api_type == "openai" else route["url"] + req_suffix

        # Rewrite model name if upstream differs
        if upstream_model != model:
            body_json["model"] = upstream_model
            raw_body = json.dumps(body_json).encode()

        if api_type == "openai":
            body_json = _anthropic_to_openai_request(body_json)
            raw_body = json.dumps(body_json).encode()

        # Build upstream headers
        base_headers: dict[str, str] = {
            k: v for k, v in request.headers.items() if k.lower() not in _SKIP_HEADERS
        }
        base_headers["content-type"] = "application/json"

        if api_type == "openai":
            base_headers = {
                k: v
                for k, v in base_headers.items()
                if k.lower() not in _ANTHROPIC_ONLY_HEADERS
            }

        upstream_headers: dict[str, str]
        if auth == "aws":
            region = route.get("aws_region", "us-east-1")
            if api_type == "openai":
                # SigV4 applied per-request via _SigV4Auth on the httpx client below
                upstream_headers = base_headers
            else:
                try:
                    sig_headers = {
                        k.lower(): v
                        for k, v in _sign_bedrock(target_url, raw_body, route).items()
                    }
                except Exception as cred_exc:
                    from botocore.exceptions import TokenRetrievalError

                    if isinstance(cred_exc, TokenRetrievalError):
                        profile = os.environ.get("AWS_PROFILE", "<profile>")
                        return self._error_response(
                            f"AWS Bedrock session expired. Run: aws sso login --profile {profile}",
                            upstream_model,
                            is_streaming,
                        )
                    raise
                upstream_headers = {**base_headers, **sig_headers}
                upstream_headers["content-type"] = "application/json"
                upstream_headers["anthropic-version"] = "2023-06-01"
            logger.info(
                "[coding-model-router] %s -> BEDROCK  region=%s  model=%s  api=%s",
                model,
                region,
                upstream_model,
                api_type,
            )
        else:  # passthrough
            upstream_headers = base_headers
            if auth_val := request.headers.get("authorization"):
                upstream_headers["authorization"] = auth_val
            logger.info(
                "[coding-model-router] %s -> ANTHROPIC  url=%s  model=%s",
                model,
                target_url,
                upstream_model,
            )

        # ── OpenAI-format route: use openai SDK + Anthropic translation ──────────
        if api_type == "openai":
            import openai

            base_url = target_url.removesuffix("/chat/completions")
            _auth_obj = _SigV4Auth(route) if auth == "aws" else None
            http_client = httpx.AsyncClient(auth=_auth_obj, timeout=None)  # nosec B113
            _placeholder_key = "dummy"  # pragma: allowlist secret
            oai_client = openai.AsyncOpenAI(
                api_key=_placeholder_key,
                base_url=base_url,
                http_client=http_client,
                max_retries=0,
            )
            oai_kwargs = {k: v for k, v in body_json.items() if k != "stream"}
            msg_id = _msg_id()
            streaming_started = False
            try:
                if is_streaming:
                    _MAX_OVERFLOW_RETRIES = 4
                    first_chunk = None
                    _original_max: int = oai_kwargs.get("max_tokens", 32768)
                    _overflow_attempt = 0
                    _throttle_attempt = 0
                    while True:
                        if _overflow_attempt > 0 or _throttle_attempt > 0:
                            await http_client.aclose()
                            http_client = httpx.AsyncClient(  # nosec B113
                                auth=_auth_obj, timeout=None
                            )
                            oai_client = openai.AsyncOpenAI(
                                api_key=_placeholder_key,
                                base_url=base_url,
                                http_client=http_client,
                                max_retries=0,
                            )
                        stream = None
                        try:
                            stream = await oai_client.chat.completions.create(
                                **oai_kwargs,
                                stream=True,
                                stream_options={"include_usage": True},
                            )
                            first_chunk = await stream.__anext__()
                            break
                        except Exception as peek_exc:
                            if stream is not None:
                                await stream.close()
                            _status = getattr(peek_exc, "status_code", None)
                            _resp_obj = getattr(peek_exc, "response", None)
                            _peek_text = getattr(_resp_obj, "text", None) or str(
                                peek_exc
                            )
                            if (
                                _CONTEXT_OVERFLOW_RE.search(str(peek_exc))
                                and _overflow_attempt < _MAX_OVERFLOW_RETRIES
                            ):
                                _overflow_attempt += 1
                                oai_kwargs["max_tokens"] = max(
                                    1, _original_max >> _overflow_attempt
                                )
                                logger.warning(
                                    "[coding-model-router] context overflow (attempt %d/%d): reducing max_tokens → %d",
                                    _overflow_attempt,
                                    _MAX_OVERFLOW_RETRIES,
                                    oai_kwargs["max_tokens"],
                                )
                            elif (
                                _status is not None
                                and _is_throttling(_status, _peek_text)
                                and _throttle_attempt < _MAX_THROTTLE_RETRIES
                            ):
                                delay = _throttle_backoff(_throttle_attempt)
                                _throttle_attempt += 1
                                logger.warning(
                                    "[coding-model-router] Bedrock throttled (attempt %d/%d): backing off %.1fs",
                                    _throttle_attempt,
                                    _MAX_THROTTLE_RETRIES,
                                    delay,
                                )
                                await asyncio.sleep(delay)
                            else:
                                raise
                    streaming_started = True
                    return StreamingResponse(
                        _oai_stream_with_cleanup(
                            stream,
                            msg_id,
                            upstream_model,
                            http_client,
                            first_chunk=first_chunk,
                        ),
                        status_code=200,
                        media_type="text/event-stream",
                    )
                else:
                    _throttle_attempt = 0
                    while True:
                        try:
                            resp = await oai_client.chat.completions.create(
                                **oai_kwargs, stream=False
                            )
                            break
                        except openai.APIStatusError as exc:
                            if (
                                _is_throttling(exc.status_code, exc.response.text)
                                and _throttle_attempt < _MAX_THROTTLE_RETRIES
                            ):
                                delay = _throttle_backoff(_throttle_attempt)
                                _throttle_attempt += 1
                                logger.warning(
                                    "[coding-model-router] Bedrock throttled (attempt %d/%d): backing off %.1fs",
                                    _throttle_attempt,
                                    _MAX_THROTTLE_RETRIES,
                                    delay,
                                )
                                await asyncio.sleep(delay)
                                continue
                            raise
                    return JSONResponse(
                        _openai_to_anthropic_response(
                            resp.model_dump(), msg_id, upstream_model
                        )
                    )
            except openai.APIStatusError as exc:
                logger.error(
                    "[coding-model-router] upstream %d: %s",
                    exc.status_code,
                    exc.response.text,
                )
                try:
                    err_body = exc.response.json()
                    err_msg = (
                        err_body.get("error", {}).get("message")
                        or err_body.get("message")
                        or exc.message
                    )
                except Exception:
                    err_msg = exc.message or str(exc)
                return self._error_response(
                    f"Bedrock error ({exc.status_code}): {err_msg}",
                    upstream_model,
                    is_streaming,
                )
            except Exception as exc:
                from botocore.exceptions import TokenRetrievalError

                _cause = exc.__cause__ or exc.__context__
                if isinstance(exc, TokenRetrievalError) or isinstance(
                    _cause, TokenRetrievalError
                ):
                    profile = os.environ.get("AWS_PROFILE", "<profile>")
                    return self._error_response(
                        f"AWS Bedrock session expired. Run: aws sso login --profile {profile}",
                        upstream_model,
                        is_streaming,
                    )
                raise
            finally:
                if not streaming_started:
                    await http_client.aclose()

        # ── Anthropic-format route: stream bytes verbatim via httpx ──────────────
        client = httpx.AsyncClient(timeout=None)  # nosec B113
        try:
            upstream_resp = await _send_with_bedrock_retry(
                client, target_url, upstream_headers, raw_body, route, auth
            )
        except Exception:
            await client.aclose()
            raise

        if upstream_resp.status_code >= 400:
            error_body = await upstream_resp.aread()
            await client.aclose()
            logger.error(
                "[coding-model-router] upstream %d from %s: %s",
                upstream_resp.status_code,
                target_url,
                error_body[:1000].decode("utf-8", errors="replace"),
            )
            return Response(
                content=error_body,
                status_code=upstream_resp.status_code,
                media_type=upstream_resp.headers.get(
                    "content-type", "application/json"
                ),
            )

        _HOP_BY_HOP = frozenset(
            {"content-encoding", "transfer-encoding", "connection", "keep-alive"}
        )
        resp_headers = {
            k: v
            for k, v in upstream_resp.headers.items()
            if k.lower() not in _HOP_BY_HOP
        }
        return StreamingResponse(
            _stream_passthrough(upstream_resp, client),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=upstream_resp.headers.get("content-type", "text/event-stream"),
        )

    @staticmethod
    def _error_response(
        text: str, model: str, is_streaming: bool
    ) -> StreamingResponse | JSONResponse:
        """Surface an error as a valid Anthropic assistant message (status 200)."""
        msg_id = _msg_id()
        if not is_streaming:
            return JSONResponse(
                {
                    "id": msg_id,
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                    "model": model,
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": len(text.split())},
                }
            )

        async def _stream() -> AsyncGenerator[bytes, None]:
            yield _sse_event(
                "message_start",
                {
                    "type": "message_start",
                    "message": {
                        "id": msg_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": model,
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                },
            )
            yield _sse_event("ping", {"type": "ping"})
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
                    "delta": {"type": "text_delta", "text": text},
                },
            )
            yield _sse_event(
                "content_block_stop", {"type": "content_block_stop", "index": 0}
            )
            yield _sse_event(
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": len(text.split())},
                },
            )
            yield _sse_event("message_stop", {"type": "message_stop"})

        return StreamingResponse(
            _stream(), status_code=200, media_type="text/event-stream"
        )

    def get_router(self) -> APIRouter:
        return self.router
