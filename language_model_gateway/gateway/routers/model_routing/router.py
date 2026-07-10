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
import inspect
import json
import logging
import os
from enum import Enum
from typing import Any, AsyncGenerator, Sequence

import httpx
from fastapi import APIRouter
from fastapi import params
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .aws_auth import SigV4Auth, _sign_bedrock
from .bedrock_client import (
    _is_throttling,
    _send_with_bedrock_retry,
    _throttle_backoff,
)
from .constants import (
    _ANTHROPIC_ONLY_HEADERS,
    _HOP_BY_HOP_HEADERS,
    _MAX_THROTTLE_RETRIES,
    _SKIP_HEADERS,
    _TOKEN_ESTIMATE_SAFETY_BUFFER,
)
from .context_manager import enforce_context_budget
from .message_translator import (
    _anthropic_to_openai_request,
    _estimate_input_tokens,
    _openai_to_anthropic_response,
)
from .route_config import _find_route
from .tokenizer import count_oai_request_tokens
from .stream_converter import (
    _msg_id,
    _oai_stream_with_cleanup,
    _oai_stream_with_usage_tracking,
    _sse_event,
    _stream_passthrough,
)
from .usage_tracker import UsageTracker

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))


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
        mongo_uri: str | None = None,
        usage_db_name: str = "llm_storage",
        usage_collection_name: str = "usage",
    ) -> None:
        self.router = APIRouter(
            prefix=prefix,
            tags=tags or ["anthropic-proxy"],
            dependencies=dependencies or [],
        )
        self._usage_tracker: UsageTracker | None = None
        if mongo_uri:
            self._usage_tracker = UsageTracker(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=usage_collection_name,
                enabled=True,
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

        # Generate request_id at the start for consistent tracing
        request_id = _msg_id()

        try:
            body_json = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.error(
                "[coding-model-router] invalid JSON body request_id=%s",
                request_id,
            )
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)

        model: str = body_json.get("model", "")
        route = _find_route(model)
        req_suffix = request.url.path[len("/v1/messages") :]

        user_id = self._get_auth_info(request).get("user_id", "unknown")
        auth_provider = self._get_auth_info(request).get("auth_provider", "unknown")

        is_fallback_route: bool = route is None
        if route is None:
            logger.error(
                "[coding-model-router] unknown model '%s' — falling back to Anthropic "
                "direct with no cost-routing or context-budget enforcement. "
                "user_id=%s request_id=%s auth_provider=%s - add a route for it in model-router-config.json",
                model, user_id, request_id, auth_provider,
            )
            route = {
                "auth": "passthrough",
                "url": "https://api.anthropic.com/v1/messages",
                "model": model,
            }

        auth: str = route["auth"]
        api_type: str = route.get("api_type", "anthropic")
        # Passthrough routes forward the client's exact model id — Anthropic is
        # authoritative on which model ids exist, so a version-bumped id must
        # never be silently overridden by a possibly-stale pinned config value.
        # Bedrock/openai routes DO rewrite to the configured backend model id,
        # since that's a genuinely different upstream model, not just a version.
        upstream_model: str = model if auth == "passthrough" else route["model"]
        is_streaming: bool = bool(body_json.get("stream"))
        tokenizer_model: str | None = route.get("tokenizer_model")

        # /count_tokens — return an accurate count when a tokenizer is configured,
        # otherwise fall back to the character-based estimate.
        if req_suffix == "/count_tokens" and api_type == "openai":
            if tokenizer_model:
                oai_body_for_count = _anthropic_to_openai_request(body_json)
                token_count = count_oai_request_tokens(
                    oai_body_for_count, tokenizer_model
                )
                if token_count is not None:
                    return JSONResponse({"input_tokens": token_count})
            return JSONResponse({"input_tokens": len(json.dumps(body_json)) // 4})

        target_url = route["url"] if api_type == "openai" else route["url"] + req_suffix

        # Rewrite model name if upstream differs
        if upstream_model != model:
            body_json["model"] = upstream_model
            raw_body = json.dumps(body_json).encode()

        # ── Context enforcement ───────────────────────────────────────────────
        #
        # Two strategies, mutually exclusive:
        #
        # A. Tokenizer-based (preferred): translate to OAI first, count tokens with
        #    the Qwen tokenizer + chat template, then compress/drop if over budget.
        #    Activated when the route has a `tokenizer_model` field.
        #
        # B. Character-based (fallback): 4-chars-per-token heuristic with 1.20× safety
        #    multiplier. Used when no tokenizer is configured.
        #
        if tokenizer_model and api_type == "openai":
            body_json = _anthropic_to_openai_request(body_json)
            body_json = enforce_context_budget(body_json, route, tokenizer_model)
            raw_body = json.dumps(body_json).encode()
        else:
            # Strategy B — character-based cap on Anthropic-format body
            route_context_window: int | None = route.get("context_window")
            route_max_tokens: int | None = route.get("max_tokens")
            if route_context_window is not None:
                estimated_input_tokens = int(_estimate_input_tokens(body_json) * 1.20)
                remaining_tokens = route_context_window - estimated_input_tokens
                requested_max = body_json.get("max_tokens", 0)
                logger.info(
                    "[coding-model-router] context window: estimated_input=%d remaining=%d requested=%d",
                    estimated_input_tokens,
                    remaining_tokens,
                    requested_max,
                )
                if remaining_tokens <= 0:
                    raw_estimate = int(estimated_input_tokens / 1.20)
                    raw_remaining = route_context_window - raw_estimate
                    logger.warning(
                        "[coding-model-router] 1.20x estimate (%d) >= context_window (%d); "
                        "raw_estimate=%d raw_remaining=%d",
                        estimated_input_tokens,
                        route_context_window,
                        raw_estimate,
                        raw_remaining,
                    )
                    if raw_remaining > 0:
                        smart_max = max(
                            1024,
                            int(raw_remaining * 0.70) - _TOKEN_ESTIMATE_SAFETY_BUFFER,
                        )
                        if route_max_tokens is not None:
                            smart_max = min(smart_max, route_max_tokens)
                        if requested_max > smart_max:
                            body_json["max_tokens"] = smart_max
                            logger.warning(
                                "[coding-model-router] overflow: seeding max_tokens=%d (raw_remaining=%d × 70%% − buffer)",
                                smart_max,
                                raw_remaining,
                            )
                else:
                    if route_max_tokens is not None:
                        effective_max_tokens = min(route_max_tokens, remaining_tokens)
                    else:
                        effective_max_tokens = remaining_tokens
                    effective_max_tokens = max(
                        1, effective_max_tokens - _TOKEN_ESTIMATE_SAFETY_BUFFER
                    )
                    if requested_max > effective_max_tokens:
                        body_json["max_tokens"] = effective_max_tokens
                        logger.info(
                            "[coding-model-router] dynamic max_tokens: capped %d → %d",
                            requested_max,
                            effective_max_tokens,
                        )

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
                # SigV4 applied per-request via SigV4Auth on the httpx client below
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
                "[coding-model-router] request_id=%s %s -> BEDROCK  region=%s  model=%s  api=%s",
                request_id,
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
                "[coding-model-router] request_id=%s %s -> ANTHROPIC  url=%s  model=%s",
                request_id,
                model,
                target_url,
                upstream_model,
            )

        # ── OpenAI-format route: use openai SDK + Anthropic translation ──────────
        if api_type == "openai":
            import openai

            base_url = target_url.removesuffix("/chat/completions")
            _auth_obj = SigV4Auth(route) if auth == "aws" else None
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
                    first_chunk = None
                    _throttle_attempt = 0
                    while True:
                        if _throttle_attempt > 0:
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
                                _close_result = stream.close()
                                if inspect.isawaitable(_close_result):
                                    await _close_result
                            _status = getattr(peek_exc, "status_code", None)
                            _resp_obj = getattr(peek_exc, "response", None)
                            _peek_text = getattr(_resp_obj, "text", None) or str(
                                peek_exc
                            )
                            if (
                                _status is not None
                                and _is_throttling(_status, _peek_text)
                                and _throttle_attempt < _MAX_THROTTLE_RETRIES
                            ):
                                delay = _throttle_backoff(_throttle_attempt)
                                _throttle_attempt += 1
                                logger.warning(
                                    "[coding-model-router] request_id=%s Bedrock throttled (attempt %d/%d): backing off %.1fs status=%s",
                                    request_id,
                                    _throttle_attempt,
                                    _MAX_THROTTLE_RETRIES,
                                    delay,
                                    _status,
                                )
                                await asyncio.sleep(delay)
                            else:
                                raise
                    streaming_started = True
                    # Create streaming response with usage tracking
                    auth_info = self._get_auth_info(request)
                    if self._usage_tracker:
                        stream_gen = _oai_stream_with_usage_tracking(
                            stream,
                            msg_id,
                            upstream_model,
                            http_client,
                            self._usage_tracker,
                            auth_info,
                            first_chunk=first_chunk,
                        )
                    else:
                        stream_gen = _oai_stream_with_cleanup(
                            stream,
                            msg_id,
                            upstream_model,
                            http_client,
                            first_chunk=first_chunk,
                        )
                    return StreamingResponse(
                        stream_gen,
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
                                    "[coding-model-router] request_id=%s Bedrock throttled (attempt %d/%d): backing off %.1fs status=%s",
                                    request_id,
                                    _throttle_attempt,
                                    _MAX_THROTTLE_RETRIES,
                                    delay,
                                    exc.status_code,
                                )
                                await asyncio.sleep(delay)
                                continue
                            raise
                    openai_response_body = resp.model_dump()
                    # Record usage before returning response
                    if self._usage_tracker:
                        input_tokens, output_tokens = self._extract_usage_from_response(
                            openai_response_body, "openai"
                        )
                        await self._usage_tracker.record_usage_from_openai_response(
                            request_id=msg_id,
                            auth_info=self._get_auth_info(request),
                            model=upstream_model,
                            response_body=openai_response_body,
                        )
                    return JSONResponse(
                        _openai_to_anthropic_response(
                            openai_response_body, msg_id, upstream_model
                        )
                    )
            except openai.APIStatusError as exc:
                user_id = self._get_auth_info(request).get("user_id", "unknown")
                logger.error(
                    "[coding-model-router] upstream %d for model=%s user_id=%s request_id=%s: %s",
                    exc.status_code,
                    upstream_model,
                    user_id,
                    msg_id,
                    exc.response.text[:200],
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
                client, target_url, upstream_headers, raw_body, route, auth, request_id
            )
        except Exception:
            await client.aclose()
            raise

        if upstream_resp.status_code >= 400:
            error_body = await upstream_resp.aread()
            await client.aclose()
            user_id = self._get_auth_info(request).get("user_id", "unknown")
            logger.error(
                "[coding-model-router] upstream %d from %s user_id=%s request_id=%s: %s",
                upstream_resp.status_code,
                target_url,
                user_id,
                request_id,
                error_body[:1000].decode("utf-8", errors="replace"),
            )
            if is_fallback_route:
                error_body = self._annotate_fallback_error(error_body, model)
            return Response(
                content=error_body,
                status_code=upstream_resp.status_code,
                media_type=upstream_resp.headers.get(
                    "content-type", "application/json"
                ),
            )

        resp_headers = {
            k: v
            for k, v in upstream_resp.headers.items()
            if k.lower() not in _HOP_BY_HOP_HEADERS
        }
        return StreamingResponse(
            _stream_passthrough(upstream_resp, client),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=upstream_resp.headers.get("content-type", "text/event-stream"),
        )

    @staticmethod
    def _annotate_fallback_error(error_body: bytes, model: str) -> bytes:
        """
        Prefix an upstream error with a note explaining that this request had
        no configured route and went directly to Anthropic — without cost-
        routing or context-budget enforcement. Without this, a fallback
        request that later hits a real context-length error just looks like
        a bare, unexplained "context exceeded" failure with no link back to
        the actual root cause (a missing/stale route entry).
        """
        note = (
            f"[language-model-gateway] model '{model}' has no configured route — "
            "this request went directly to Anthropic without cost-routing or "
            "context-budget enforcement. Original error: "
        )
        try:
            parsed = json.loads(error_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return note.encode() + error_body
        error_obj = parsed.get("error")
        if isinstance(error_obj, dict) and isinstance(error_obj.get("message"), str):
            error_obj["message"] = note + error_obj["message"]
            return json.dumps(parsed).encode()
        return note.encode() + error_body

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

    def _get_auth_info(self, request: Request) -> dict[str, Any]:
        """Extract auth information from the request headers."""
        auth_info: dict[str, Any] = {"headers": dict(request.headers)}

        # Extract user info from x-openwebui headers (preferred) or legacy headers
        if user_id := request.headers.get("x-openwebui-user-id"):
            auth_info["user_id"] = user_id
        elif user_id := request.headers.get("x-customer-id"):
            auth_info["user_id"] = user_id

        if auth_provider := request.headers.get("x-auth-provider"):
            auth_info["auth_provider"] = auth_provider

        if email := request.headers.get("x-openwebui-user-email"):
            auth_info["email"] = email
        elif email := request.headers.get("x-email"):
            auth_info["email"] = email

        if user_name := request.headers.get("x-openwebui-user-name"):
            auth_info["user_name"] = user_name
        elif user_name := request.headers.get("x-user-name"):
            auth_info["user_name"] = user_name

        return auth_info

    def _extract_usage_from_response(
        self, response_body: dict[str, Any], api_type: str
    ) -> tuple[int, int]:
        """Extract input and output tokens from a response body."""
        if api_type == "openai":
            usage = response_body.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
        else:
            usage = response_body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        return input_tokens, output_tokens
