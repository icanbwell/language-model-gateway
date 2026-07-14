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
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Sequence, cast

import httpx
from fastapi import APIRouter
from fastapi import params
from opentelemetry import trace
from oidcauthlib.auth.exceptions.authorization_bearer_token_expired_exception import (
    AuthorizationBearerTokenExpiredException,
)
from oidcauthlib.auth.exceptions.authorization_bearer_token_invalid_exception import (
    AuthorizationBearerTokenInvalidException,
)
from oidcauthlib.auth.token_reader import TokenReader
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .aws_auth import SigV4Auth, _bedrock_credential_error_detail, _sign_bedrock
from .bedrock_client import (
    _is_throttling,
    _is_transient_stream_error,
    _send_with_bedrock_retry,
    _throttle_backoff,
)
from . import bedrock_converse_client
from .bedrock_converse_client import (
    _converse_response_to_anthropic,
    _is_transient_bedrock_error_code,
    _openai_to_converse_request,
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
    _anthropic_content_to_text,
    _anthropic_to_openai_request,
    _estimate_input_tokens,
    _openai_to_anthropic_response,
)
from .route_config import _find_route
from .tokenizer import count_oai_request_tokens
from .stream_converter import (
    _fire_and_forget,
    _msg_id,
    _oai_stream_with_cleanup,
    _oai_stream_with_usage_tracking,
    _sse_event,
    _stream_passthrough,
    _stream_passthrough_with_usage_tracking,
)
from .account_directory import (
    AccountDirectory,
    extract_account_uuid,
    extract_session_id,
)
from .error_tracker import ErrorTracker
from .usage_tracker import UsageTracker

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))


def _extract_last_user_text(body_json: dict[str, Any]) -> str | None:
    """Extract the text of the most recent user message, for usage-record previews."""
    messages = body_json.get("messages")
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            text = _anthropic_content_to_text(message.get("content") or "")
            return text or None
    return None


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
        usage_session_collection_name: str = "usage_sessions",
        usage_track_sessions: bool = True,
        usage_capture_previews: bool = False,
        usage_preview_chars: int = 100,
        error_collection_name: str = "errors",
        account_directory_collection_name: str = "account_directory",
        token_reader: TokenReader | None = None,
        debug_log_received_oauth_tokens: bool = False,
        custom_header_prefix: str = "x-model-routing-",
        bedrock_transport: str = "mantle",
    ) -> None:
        self.router = APIRouter(
            prefix=prefix,
            tags=tags or ["anthropic-proxy"],
            dependencies=dependencies or [],
        )
        self._token_reader: TokenReader | None = token_reader
        self._custom_header_prefix: str = custom_header_prefix.lower()
        self._bedrock_transport: str = bedrock_transport
        self._debug_log_received_oauth_tokens: bool = debug_log_received_oauth_tokens
        if self._debug_log_received_oauth_tokens:
            logger.warning(
                "[coding-model-router] DEBUG_LOG_RECEIVED_OAUTH_TOKENS is enabled — "
                "full request headers (including raw Authorization tokens) and "
                "bodies will be written to logs. Local development only; never "
                "enable this in a shared or deployed environment."
            )
        self._usage_tracker: UsageTracker | None = None
        self._error_tracker: ErrorTracker | None = None
        self._account_directory: AccountDirectory | None = None
        if mongo_uri:
            self._usage_tracker = UsageTracker(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=usage_collection_name,
                session_collection_name=usage_session_collection_name,
                enabled=True,
                track_sessions=usage_track_sessions,
                capture_previews=usage_capture_previews,
                preview_chars=usage_preview_chars,
            )
            self._error_tracker = ErrorTracker(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=error_collection_name,
                enabled=True,
            )
            self._account_directory = AccountDirectory(
                mongo_uri=mongo_uri,
                db_name=usage_db_name,
                collection_name=account_directory_collection_name,
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
        self, request: Request, background_tasks: BackgroundTasks
    ) -> StreamingResponse | JSONResponse | Response:
        # Captured before any parsing/upstream work so the usage record's
        # duration reflects the client's full wait, not just upstream time.
        request_start_time = datetime.now(timezone.utc)
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

        if self._debug_log_received_oauth_tokens:
            logger.warning(
                "[coding-model-router] DEBUG received request (local-debug only, do "
                "not enable in shared environments) request_id=%s method=%s path=%s "
                "headers=%s body=%s",
                request_id,
                request.method,
                request.url.path,
                dict(request.headers),
                body_json,
            )

        model: str = body_json.get("model", "")
        route = _find_route(model)
        req_suffix = request.url.path[len("/v1/messages") :]

        auth_info = await self._get_auth_info(request)
        self._attach_account_uuid(auth_info, body_json)
        self._attach_claude_code_headers(auth_info, request, body_json)
        user_id = auth_info.get("user_id", "unknown")
        auth_provider = auth_info.get("auth_provider", "unknown")
        prompt_text = _extract_last_user_text(body_json)
        accept_encoding = request.headers.get("accept-encoding")

        is_fallback_route: bool = route is None
        if route is None:
            logger.error(
                "[coding-model-router] unknown model '%s' — falling back to Anthropic "
                "direct with no cost-routing or context-budget enforcement. "
                "user_id=%s request_id=%s auth_provider=%s - add a route for it in model-router-config.json",
                model,
                user_id,
                request_id,
                auth_provider,
            )
            route = {
                "auth": "passthrough",
                "url": "https://api.anthropic.com/v1/messages",
                "model": model,
            }

        auth: str = route["auth"]
        api_type: str = route.get("api_type", "anthropic")
        model_tier: str = route.get("tier", "unknown")
        backend: str = "anthropic" if auth == "passthrough" else "aws_bedrock"
        price_per_mtok: float | None = route.get("price_per_mtok")
        anthropic_price_per_mtok: float | None = route.get("anthropic_price_per_mtok")
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
            k: v
            for k, v in request.headers.items()
            if k.lower() not in _SKIP_HEADERS
            and not k.lower().startswith(self._custom_header_prefix)
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
                    detail = _bedrock_credential_error_detail(cred_exc)
                    if detail is not None:
                        error_type, message = detail
                        self._record_error(
                            request_id=request_id,
                            auth_info=auth_info,
                            model=upstream_model,
                            error_type=error_type,
                            error_message=str(cred_exc),
                            start_time=request_start_time,
                            model_tier=model_tier,
                            backend=backend,
                            auth=auth,
                            api_type=api_type,
                            streaming=is_streaming,
                        )
                        return self._error_response(
                            message, upstream_model, is_streaming
                        )
                    raise
                upstream_headers = {**base_headers, **sig_headers}
                upstream_headers["content-type"] = "application/json"
                upstream_headers["anthropic-version"] = "2023-06-01"
            logger.info(
                "[coding-model-router] request_id=%s %s -> BEDROCK  region=%s  model=%s  api=%s  streaming=%s",
                request_id,
                model,
                region,
                upstream_model,
                api_type,
                is_streaming,
            )
        else:  # passthrough
            upstream_headers = base_headers
            if auth_val := request.headers.get("authorization"):
                upstream_headers["authorization"] = auth_val
            logger.info(
                "[coding-model-router] request_id=%s %s -> ANTHROPIC  url=%s  model=%s  streaming=%s",
                request_id,
                model,
                target_url,
                upstream_model,
                is_streaming,
            )

        dispatch_start = time.perf_counter()

        # ── Native Bedrock Converse route: manual fallback for Bedrock Mantle ──
        if (
            api_type == "openai"
            and auth == "aws"
            and self._bedrock_transport == "native"
        ):
            if is_streaming:
                # _dispatch_bedrock_native_streaming doesn't exist yet — added by
                # the next task. Remove this type: ignore when that lands.
                return await self._dispatch_bedrock_native_streaming(  # type: ignore[attr-defined,no-any-return]
                    route=route,
                    body_json=body_json,
                    upstream_model=upstream_model,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    price_per_mtok=price_per_mtok,
                    anthropic_price_per_mtok=anthropic_price_per_mtok,
                    prompt_text=prompt_text,
                    accept_encoding=accept_encoding,
                    request=request,
                    request_id=request_id,
                    auth_info=auth_info,
                    request_start_time=request_start_time,
                    dispatch_start=dispatch_start,
                )
            return await self._dispatch_bedrock_native_nonstreaming(
                route=route,
                body_json=body_json,
                upstream_model=upstream_model,
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                prompt_text=prompt_text,
                accept_encoding=accept_encoding,
                request_id=request_id,
                auth_info=auth_info,
                request_start_time=request_start_time,
                dispatch_start=dispatch_start,
                background_tasks=background_tasks,
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
            # Bound here (not just inside `if is_streaming:`) so the bare
            # openai.APIError handler below can safely check it regardless of
            # which branch ran — it's only ever non-None for the streaming path.
            stream = None
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
                            # A plain openai.APIError (SSE `{"error": {...}}`
                            # mid-stream, e.g. Bedrock Mantle) has no
                            # .status_code at all — _is_throttling can't apply,
                            # so it needs its own transient/permanent check
                            # instead of skipping retry entirely.
                            _retryable = (
                                _is_throttling(_status, _peek_text)
                                if _status is not None
                                else _is_transient_stream_error(
                                    getattr(peek_exc, "code", None),
                                    getattr(peek_exc, "type", None),
                                    _peek_text,
                                )
                            )
                            if _retryable and _throttle_attempt < _MAX_THROTTLE_RETRIES:
                                delay = _throttle_backoff(_throttle_attempt)
                                _throttle_attempt += 1
                                logger.warning(
                                    "[coding-model-router] request_id=%s Bedrock throttled (attempt %d/%d): backing off %.1fs status=%s code=%s",
                                    request_id,
                                    _throttle_attempt,
                                    _MAX_THROTTLE_RETRIES,
                                    delay,
                                    _status,
                                    getattr(peek_exc, "code", None),
                                )
                                await asyncio.sleep(delay)
                            else:
                                raise
                    streaming_started = True
                    self._record_upstream_latency(
                        dispatch_start,
                        model_tier=model_tier,
                        upstream_model=upstream_model,
                        auth=auth,
                        api_type=api_type,
                    )

                    # Record mid-stream Bedrock Mantle failures the same way as
                    # the pre-first-chunk case above — otherwise a failure
                    # after streaming has already started is only ever shown
                    # inline to the client and never reaches model-router-errors.
                    def _record_mid_stream_error(message: str) -> None:
                        self._record_error(
                            request_id=msg_id,
                            auth_info=auth_info,
                            model=upstream_model,
                            error_type="bedrock_stream_error",
                            error_message=message,
                            start_time=request_start_time,
                            model_tier=model_tier,
                            backend=backend,
                            auth=auth,
                            api_type=api_type,
                            streaming=True,
                            # The initial handshake response — headers only,
                            # since the error body itself arrived as a later
                            # SSE event on this same response, not a fresh one.
                            response_headers=dict(stream.response.headers),
                        )

                    # Create streaming response with usage tracking
                    if self._usage_tracker:
                        stream_gen = _oai_stream_with_usage_tracking(
                            stream,
                            msg_id,
                            upstream_model,
                            http_client,
                            self._usage_tracker,
                            auth_info,
                            first_chunk=first_chunk,
                            prompt_text=prompt_text,
                            model_tier=model_tier,
                            backend=backend,
                            price_per_mtok=price_per_mtok,
                            anthropic_price_per_mtok=anthropic_price_per_mtok,
                            streaming=True,
                            compression_requested=accept_encoding,
                            # This response's media_type is text/event-stream,
                            # which GZipMiddleware hardcodes into its excluded
                            # content types (see api.py) — never compressed,
                            # regardless of what the client's Accept-Encoding
                            # offers.
                            compression_used="none",
                            request=request,
                            start_time=request_start_time,
                            on_stream_error=_record_mid_stream_error,
                        )
                    else:
                        stream_gen = _oai_stream_with_cleanup(
                            stream,
                            msg_id,
                            upstream_model,
                            http_client,
                            first_chunk=first_chunk,
                            request=request,
                            on_stream_error=_record_mid_stream_error,
                        )
                    return StreamingResponse(
                        stream_gen,
                        status_code=200,
                        media_type="text/event-stream",
                        # Tells nginx/ingress not to buffer this response —
                        # without it, a reverse proxy with default buffering
                        # would hold the entire SSE stream until it completes
                        # before forwarding any of it to the client.
                        headers={"X-Accel-Buffering": "no"},
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
                    self._record_upstream_latency(
                        dispatch_start,
                        model_tier=model_tier,
                        upstream_model=upstream_model,
                        auth=auth,
                        api_type=api_type,
                    )
                    openai_response_body = resp.model_dump()
                    response = JSONResponse(
                        _openai_to_anthropic_response(
                            openai_response_body, msg_id, upstream_model
                        )
                    )
                    # GZipMiddleware (added in api.py) only compresses non-streaming
                    # responses at least 500 bytes when the client's Accept-Encoding
                    # allows gzip — predict its decision now, before it runs, since
                    # the usage record is written from a background task after this
                    # response is already on its way out.
                    compression_used = (
                        "gzip"
                        if accept_encoding
                        and "gzip" in accept_encoding.lower()
                        and len(response.body) >= 500
                        else "none"
                    )
                    # Record usage after the response is sent to the client, not before.
                    if self._usage_tracker:
                        background_tasks.add_task(
                            self._usage_tracker.record_usage_from_openai_response,
                            request_id=msg_id,
                            auth_info=auth_info,
                            model=upstream_model,
                            response_body=openai_response_body,
                            prompt_text=prompt_text,
                            model_tier=model_tier,
                            backend=backend,
                            price_per_mtok=price_per_mtok,
                            anthropic_price_per_mtok=anthropic_price_per_mtok,
                            streaming=False,
                            compression_requested=accept_encoding,
                            compression_used=compression_used,
                            start_time=request_start_time,
                        )
                    response.background = background_tasks
                    return response
            except openai.APIStatusError as exc:
                logger.error(
                    "[coding-model-router] Bedrock Mantle upstream error: status=%d "
                    "model=%s auth=%s user_id=%s request_id=%s streaming=%s body=%s",
                    exc.status_code,
                    upstream_model,
                    auth,
                    user_id,
                    msg_id,
                    is_streaming,
                    exc.response.text[:1000],
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
                self._record_error(
                    request_id=msg_id,
                    auth_info=auth_info,
                    model=upstream_model,
                    error_type="bedrock_upstream_error",
                    error_message=exc.response.text,
                    start_time=request_start_time,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    streaming=is_streaming,
                    status_code=exc.status_code,
                    response_headers=dict(exc.response.headers),
                )
                return self._error_response(
                    f"Bedrock error ({exc.status_code}): {err_msg}",
                    upstream_model,
                    is_streaming,
                )
            except openai.APIError as exc:
                if type(exc) is not openai.APIError:
                    # A genuine transport failure (dropped connection, timeout,
                    # malformed response) — not a Bedrock error body embedded
                    # in an SSE event. exc.code/type/param/body are always
                    # None on these subclasses, so recording this as
                    # "bedrock_stream_error" would just be a null-filled,
                    # misleading record. Route it through the same handling
                    # as any other unexpected exception instead.
                    return self._handle_unexpected_upstream_error(
                        exc,
                        request_id=msg_id,
                        auth_info=auth_info,
                        upstream_model=upstream_model,
                        request_start_time=request_start_time,
                        model_tier=model_tier,
                        backend=backend,
                        auth=auth,
                        api_type=api_type,
                        streaming=is_streaming,
                        user_id=user_id,
                    )
                # Raised by the SDK for errors embedded in an SSE data event
                # (no HTTP status code involved) — e.g. Bedrock Mantle sends
                # `{"error": {...}}` mid-stream instead of a 4xx/5xx response.
                # exc.body is the raw error payload; capture it verbatim since
                # str(exc) alone is a generic, unhelpful message.
                logger.error(
                    "[coding-model-router] Bedrock Mantle stream error: "
                    "model=%s auth=%s user_id=%s request_id=%s streaming=%s "
                    "code=%s type=%s param=%s body=%s",
                    upstream_model,
                    auth,
                    user_id,
                    msg_id,
                    is_streaming,
                    exc.code,
                    exc.type,
                    exc.param,
                    exc.body,
                )
                self._record_error(
                    request_id=msg_id,
                    auth_info=auth_info,
                    model=upstream_model,
                    error_type="bedrock_stream_error",
                    error_message=json.dumps(
                        {
                            "message": exc.message,
                            "code": exc.code,
                            "type": exc.type,
                            "param": exc.param,
                            "body": exc.body,
                        },
                        default=str,
                    ),
                    start_time=request_start_time,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    streaming=is_streaming,
                    # Headers from the initial (successful) handshake response —
                    # the error itself arrived as a later SSE event on this same
                    # response, so there's no separate error-response to read
                    # headers from. `stream` is always assigned by this point:
                    # a bare openai.APIError (as opposed to APIConnectionError,
                    # filtered out above) only happens after the SSE body has
                    # started decoding.
                    response_headers=(
                        dict(stream.response.headers) if stream is not None else None
                    ),
                )
                # Surface whatever detail Bedrock actually sent (not just
                # exc.message, which can itself be a generic passthrough
                # string) so the client sees the same diagnostic info now
                # captured in model-router-errors, instead of a vaguer
                # message than what's on record.
                _extra_detail = (
                    {k: v for k, v in exc.body.items() if k != "message"}
                    if isinstance(exc.body, dict)
                    else None
                )
                client_text = f"Bedrock stream error: {exc.message}"
                if _extra_detail:
                    client_text += f" ({json.dumps(_extra_detail, default=str)})"
                return self._error_response(
                    client_text,
                    upstream_model,
                    is_streaming,
                )
            except Exception as exc:
                return self._handle_unexpected_upstream_error(
                    exc,
                    request_id=msg_id,
                    auth_info=auth_info,
                    upstream_model=upstream_model,
                    request_start_time=request_start_time,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    streaming=is_streaming,
                    user_id=user_id,
                )
            finally:
                if not streaming_started:
                    await http_client.aclose()

        # ── Anthropic-format route: stream bytes verbatim via httpx ──────────────
        client = httpx.AsyncClient(timeout=None)  # nosec B113
        try:
            upstream_resp = await _send_with_bedrock_retry(
                client, target_url, upstream_headers, raw_body, route, auth, request_id
            )
        except Exception as exc:
            await client.aclose()
            # Previously re-raised with no record at all — a connection
            # failure/timeout dispatching to Anthropic/Bedrock became a bare
            # 500 with zero trace in model-router-errors.
            logger.error(
                "[coding-model-router] passthrough dispatch failed: url=%s "
                "model=%s auth=%s user_id=%s request_id=%s streaming=%s: %s",
                target_url,
                upstream_model,
                auth,
                user_id,
                request_id,
                is_streaming,
                exc,
                exc_info=True,
            )
            self._record_error(
                request_id=request_id,
                auth_info=auth_info,
                model=upstream_model,
                error_type=type(exc).__name__,
                error_message=str(exc),
                start_time=request_start_time,
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                streaming=is_streaming,
            )
            raise

        self._record_upstream_latency(
            dispatch_start,
            model_tier=model_tier,
            upstream_model=upstream_model,
            auth=auth,
            api_type=api_type,
        )

        if upstream_resp.status_code >= 400:
            error_body = await upstream_resp.aread()
            await client.aclose()

            logger.error(
                "[coding-model-router] upstream %d from %s user_id=%s request_id=%s: %s",
                upstream_resp.status_code,
                target_url,
                user_id,
                request_id,
                error_body[:1000].decode("utf-8", errors="replace"),
            )
            self._record_error(
                request_id=request_id,
                auth_info=auth_info,
                model=upstream_model,
                error_type="upstream_error",
                error_message=error_body[:1000].decode("utf-8", errors="replace"),
                start_time=request_start_time,
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                streaming=is_streaming,
                status_code=upstream_resp.status_code,
            )

            if is_fallback_route:
                # For fallback routes, annotate with context about missing route
                error_body = self._annotate_fallback_error(error_body, model)

            # Parse once, after annotation, so the passthrough decision and
            # the wrapped message (if any) are always derived from the exact
            # bytes about to be sent to the client — previously these were
            # two separate json.loads calls with two different criteria,
            # which could disagree (e.g. the wrap branch using a clean_error
            # computed from the pre-annotation body).
            try:
                parsed = json.loads(error_body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None

            if self._upstream_error_is_well_formed(parsed):
                final_content = error_body
            else:
                clean_error = self._extract_clean_error(
                    parsed, error_body, upstream_resp.status_code
                )
                final_content = json.dumps({"error": {"message": clean_error}}).encode()

            return Response(
                content=final_content,
                status_code=upstream_resp.status_code,
                media_type="application/json",
            )

        resp_headers = {
            k: v
            for k, v in upstream_resp.headers.items()
            if k.lower() not in _HOP_BY_HOP_HEADERS
        }
        # See the comment on the other StreamingResponse construction above —
        # tells nginx/ingress not to buffer this response before relaying it.
        resp_headers["X-Accel-Buffering"] = "no"

        if not is_streaming:
            # Anthropic's non-streaming response is a single JSON blob, so
            # there's no byte-relay benefit to keeping it as a StreamingResponse
            # — buffer it (same as the >=400 branch above already does) so
            # usage can be extracted the same way the openai-format route does.
            body_bytes = await upstream_resp.aread()
            await upstream_resp.aclose()
            await client.aclose()
            if self._usage_tracker:
                try:
                    response_body = json.loads(body_bytes)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response_body = None
                if response_body is not None:
                    compression_used = (
                        "gzip"
                        if accept_encoding
                        and "gzip" in accept_encoding.lower()
                        and len(body_bytes) >= 500
                        else "none"
                    )
                    background_tasks.add_task(
                        self._usage_tracker.record_usage_from_anthropic_response,
                        request_id=request_id,
                        auth_info=auth_info,
                        model=upstream_model,
                        response_body=response_body,
                        model_tier=model_tier,
                        backend=backend,
                        price_per_mtok=price_per_mtok,
                        anthropic_price_per_mtok=anthropic_price_per_mtok,
                        streaming=False,
                        compression_requested=accept_encoding,
                        compression_used=compression_used,
                        prompt_text=prompt_text,
                        start_time=request_start_time,
                    )
            passthrough_response = Response(
                content=body_bytes,
                status_code=upstream_resp.status_code,
                headers=resp_headers,
                media_type=upstream_resp.headers.get(
                    "content-type", "application/json"
                ),
            )
            passthrough_response.background = background_tasks
            return passthrough_response

        if self._usage_tracker:
            stream_gen = _stream_passthrough_with_usage_tracking(
                upstream_resp,
                client,
                self._usage_tracker,
                request_id,
                auth_info,
                upstream_model,
                request_start_time,
                prompt_text=prompt_text,
                model_tier=model_tier,
                backend=backend,
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                compression_requested=accept_encoding,
                # Same reasoning as the openai-format route's streaming
                # response — text/event-stream is excluded from GZipMiddleware
                # regardless of what the client's Accept-Encoding offers.
                compression_used="none",
                request=request,
            )
        else:
            stream_gen = _stream_passthrough(upstream_resp, client, request=request)

        return StreamingResponse(
            stream_gen,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=upstream_resp.headers.get("content-type", "text/event-stream"),
        )

    def _record_error(
        self,
        *,
        request_id: str,
        auth_info: dict[str, Any],
        model: str,
        error_type: str,
        error_message: str,
        start_time: datetime,
        model_tier: str | None = None,
        backend: str | None = None,
        auth: str | None = None,
        api_type: str | None = None,
        streaming: bool | None = None,
        status_code: int | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> None:
        """Fire-and-forget an error record — never blocks or masks the caller's
        own error handling (raising/returning the client-facing error response).
        """
        if self._error_tracker is None:
            return
        _fire_and_forget(
            self._error_tracker.record_error(
                request_id=request_id,
                model=model,
                error_type=error_type,
                error_message=error_message,
                start_time=start_time,
                user_id=auth_info.get("user_id"),
                session_id=auth_info.get("session_id"),
                account_uuid=auth_info.get("account_uuid"),
                agent_id=auth_info.get("agent_id"),
                parent_agent_id=auth_info.get("parent_agent_id"),
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                streaming=streaming,
                status_code=status_code,
                response_headers=response_headers,
            )
        )

    async def _dispatch_bedrock_native_nonstreaming(
        self,
        *,
        route: dict[str, Any],
        body_json: dict[str, Any],
        upstream_model: str,
        model_tier: str,
        backend: str,
        auth: str,
        api_type: str,
        price_per_mtok: float | None,
        anthropic_price_per_mtok: float | None,
        prompt_text: str | None,
        accept_encoding: str | None,
        request_id: str,
        auth_info: dict[str, Any],
        request_start_time: datetime,
        dispatch_start: float,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        """Non-streaming counterpart to the openai-SDK Mantle dispatch, for
        auth="aws" routes when self._bedrock_transport == "native".
        """
        from botocore.exceptions import (
            ClientError,
            NoCredentialsError,
            TokenRetrievalError,
        )

        msg_id = _msg_id()
        bedrock_client = bedrock_converse_client._get_bedrock_runtime_client(route)
        converse_kwargs = _openai_to_converse_request(body_json, route["model"])

        throttle_attempt = 0
        while True:
            try:
                resp = await asyncio.to_thread(
                    bedrock_client.converse, **converse_kwargs
                )
                break
            except (NoCredentialsError, TokenRetrievalError) as cred_exc:
                detail = _bedrock_credential_error_detail(cred_exc)
                if detail is None:
                    raise
                error_type, message = detail
                self._record_error(
                    request_id=request_id,
                    auth_info=auth_info,
                    model=upstream_model,
                    error_type=error_type,
                    error_message=str(cred_exc),
                    start_time=request_start_time,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    streaming=False,
                )
                # is_streaming is always False here — _error_response's
                # streaming/non-streaming return type only varies on that
                # argument, so this is always a JSONResponse in practice.
                return cast(
                    JSONResponse, self._error_response(message, upstream_model, False)
                )
            except ClientError as exc:
                error_info = exc.response.get("Error", {})
                error_code = error_info.get("Code", "")
                error_message_text = error_info.get("Message", "")
                aws_request_id = exc.response.get("ResponseMetadata", {}).get(
                    "RequestId"
                )
                if (
                    _is_transient_bedrock_error_code(error_code)
                    and throttle_attempt < _MAX_THROTTLE_RETRIES
                ):
                    delay = _throttle_backoff(throttle_attempt)
                    throttle_attempt += 1
                    logger.warning(
                        "[coding-model-router] request_id=%s native Bedrock throttled "
                        "(attempt %d/%d): backing off %.1fs code=%s",
                        request_id,
                        throttle_attempt,
                        _MAX_THROTTLE_RETRIES,
                        delay,
                        error_code,
                    )
                    await asyncio.sleep(delay)
                    continue
                self._record_error(
                    request_id=request_id,
                    auth_info=auth_info,
                    model=upstream_model,
                    error_type="bedrock_native_error",
                    error_message=json.dumps(
                        {
                            "code": error_code,
                            "message": error_message_text,
                            "request_id": aws_request_id,
                        }
                    ),
                    start_time=request_start_time,
                    model_tier=model_tier,
                    backend=backend,
                    auth=auth,
                    api_type=api_type,
                    streaming=False,
                )
                return cast(
                    JSONResponse,
                    self._error_response(
                        f"Bedrock error ({error_code}): {error_message_text}",
                        upstream_model,
                        False,
                    ),
                )

        self._record_upstream_latency(
            dispatch_start,
            model_tier=model_tier,
            upstream_model=upstream_model,
            auth=auth,
            api_type=api_type,
        )
        anthropic_response = _converse_response_to_anthropic(
            resp, msg_id, upstream_model
        )
        response = JSONResponse(anthropic_response)
        if self._usage_tracker:
            usage = resp.get("usage", {})
            background_tasks.add_task(
                self._usage_tracker.record_usage,
                request_id=msg_id,
                user_id=auth_info.get("user_id"),
                model=upstream_model,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
                start_time=request_start_time,
                auth_provider=auth_info.get("auth_provider"),
                email=auth_info.get("email"),
                user_name=auth_info.get("user_name"),
                session_id=auth_info.get("session_id"),
                account_uuid=auth_info.get("account_uuid"),
                agent_id=auth_info.get("agent_id"),
                parent_agent_id=auth_info.get("parent_agent_id"),
                model_tier=model_tier,
                backend=backend,
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                streaming=False,
                compression_requested=accept_encoding,
                compression_used="none",
                custom_headers=auth_info.get("custom_headers"),
                prompt_text=prompt_text,
                response_text=None,
            )
        response.background = background_tasks
        return response

    def _handle_unexpected_upstream_error(
        self,
        exc: Exception,
        *,
        request_id: str,
        auth_info: dict[str, Any],
        upstream_model: str,
        request_start_time: datetime,
        model_tier: str | None,
        backend: str | None,
        auth: str | None,
        api_type: str | None,
        streaming: bool,
        user_id: str | None,
    ) -> StreamingResponse | JSONResponse:
        """Classify, record, and re-raise an exception that isn't one of the
        specific Bedrock/OpenAI error shapes handled above it.

        Shared by the generic `except Exception` handler and by
        `openai.APIError` subclasses (`APIConnectionError`, `APITimeoutError`,
        `APIResponseValidationError`) that carry no `code`/`type`/`param`/
        `body` — those aren't genuine mid-stream Bedrock error bodies and
        must not be recorded as `bedrock_stream_error`. Sibling `except`
        clauses on one `try` don't chain, so callers can't get here via a
        bare `raise` from another clause — they must call this directly.

        Must be called from within an active `except` block: it ends with a
        bare `raise`, which re-raises whatever exception is currently being
        handled by the caller.
        """
        detail = _bedrock_credential_error_detail(exc)
        if detail is not None:
            error_type, message = detail
            self._record_error(
                request_id=request_id,
                auth_info=auth_info,
                model=upstream_model,
                error_type=error_type,
                error_message=str(exc),
                start_time=request_start_time,
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                streaming=streaming,
            )
            return self._error_response(message, upstream_model, streaming)
        logger.error(
            "[coding-model-router] Bedrock Mantle request failed with an "
            "unexpected %s: model=%s auth=%s user_id=%s request_id=%s "
            "streaming=%s: %s",
            type(exc).__name__,
            upstream_model,
            auth,
            user_id,
            request_id,
            streaming,
            exc,
            exc_info=True,
        )
        self._record_error(
            request_id=request_id,
            auth_info=auth_info,
            model=upstream_model,
            error_type=type(exc).__name__,
            error_message=str(exc),
            start_time=request_start_time,
            model_tier=model_tier,
            backend=backend,
            auth=auth,
            api_type=api_type,
            streaming=streaming,
        )
        raise

    @staticmethod
    def _record_upstream_latency(
        dispatch_start: float,
        *,
        model_tier: str,
        upstream_model: str,
        auth: str,
        api_type: str,
    ) -> None:
        """Record time-to-first-response-from-upstream on the current span.

        This is the proxy's own processing latency — time until Anthropic/
        Bedrock starts responding — not total streaming duration, which is
        dominated by the upstream model's own token-generation speed rather
        than anything this router controls.
        """
        latency_ms = (time.perf_counter() - dispatch_start) * 1000
        span = trace.get_current_span()
        span.set_attribute("model_tier", model_tier)
        span.set_attribute("upstream_model", upstream_model)
        span.set_attribute("auth_strategy", auth)
        span.set_attribute("api_type", api_type)
        span.set_attribute("upstream_latency_ms", latency_ms)

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
    def _upstream_error_is_well_formed(parsed: Any) -> bool:
        """Whether `parsed` (the result of `json.loads`-ing an upstream error
        body, or `None` if that failed) is already a `{"error": {"message":
        str}}` or `{"error": str}` body worth passing through to the client
        verbatim, rather than wrapping via `_extract_clean_error`.
        """
        if not isinstance(parsed, dict) or "error" not in parsed:
            return False
        err = parsed["error"]
        return isinstance(err, str) or (
            isinstance(err, dict) and isinstance(err.get("message"), str)
        )

    @staticmethod
    def _extract_clean_error(parsed: Any, error_body: bytes, status_code: int) -> str:
        """Pull a client-safe message out of an upstream error body that
        `_upstream_error_is_well_formed` rejected — `parsed` may still be a
        JSON value (just not the expected error shape), or `None` if the
        body wasn't valid JSON at all.
        """
        if isinstance(parsed, dict):
            if "error" in parsed:
                return f"Error: {json.dumps(parsed['error'], default=str)}"
            message = parsed.get("message")
            if isinstance(message, str):
                return message
            return f"Error response (status {status_code})"
        if parsed is not None:
            return f"Error: {json.dumps(parsed, default=str)}"
        return (
            error_body[:500].decode("utf-8", errors="replace")
            or f"Unknown error (status {status_code})"
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
            _stream(),
            status_code=200,
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    def get_router(self) -> APIRouter:
        return self.router

    def _attach_account_uuid(
        self, auth_info: dict[str, Any], body_json: dict[str, Any]
    ) -> None:
        """Record Claude Code's account_uuid on auth_info, unresolved.

        _get_auth_info only populates auth_info["user_id"] when the caller's
        Authorization header verifies as a genuine OIDC token — which never
        happens for real Claude Code traffic, since that header is always the
        client's own Anthropic subscription OAuth token. account_uuid is
        stored as-is on the usage record instead; account_uuid -> email
        resolution happens downstream in reporting, not in this hot path.

        self._account_directory is intentionally unused here — it's still
        constructed so the model-router-account-directory collection exists
        for that downstream reporting join, but this router no longer queries
        it live.
        """
        account_uuid = extract_account_uuid(body_json)
        if account_uuid:
            auth_info["account_uuid"] = account_uuid

    def _attach_claude_code_headers(
        self, auth_info: dict[str, Any], request: Request, body_json: dict[str, Any]
    ) -> None:
        """Record Claude Code's session/subagent identity headers on auth_info.

        Per the documented gateway protocol
        (https://code.claude.com/docs/en/llm-gateway-protocol):
        - `x-claude-code-session-id` uniquely identifies the CLI session —
          the officially documented source, preferred over parsing
          `body.metadata.user_id` (a reverse-engineered fallback used before
          this header was confirmed; still used when the header is absent).
        - `x-claude-code-agent-id`/`x-claude-code-parent-agent-id` identify a
          subagent Claude Code spawned and its parent, present only on
          requests from an agent — not a person or device identifier. Used
          alongside session_id to attribute cost to parallel subagents.
        """
        auth_info["session_id"] = request.headers.get(
            "x-claude-code-session-id"
        ) or extract_session_id(body_json)
        if agent_id := request.headers.get("x-claude-code-agent-id"):
            auth_info["agent_id"] = agent_id
        if parent_agent_id := request.headers.get("x-claude-code-parent-agent-id"):
            auth_info["parent_agent_id"] = parent_agent_id

    async def _get_auth_info(self, request: Request) -> dict[str, Any]:
        """Extract auth information from the request headers.

        The `Authorization` header on this router is the client's own
        upstream Anthropic/Bedrock credential (forwarded as-is — see class
        docstring), not necessarily a b.well-issued OIDC token, so it cannot
        be used to gate the proxy call itself. It CAN be used to decide
        whether user-identification headers (`x-openwebui-user-id` etc.) are
        trustworthy for usage-tracking attribution: those headers are fully
        caller-controlled and otherwise trivially spoofable (IDOR), so they
        are only honored when `Authorization` verifies as a genuine,
        signature-checked OIDC token. Otherwise usage is recorded with no
        user_id rather than a spoofable one — this never blocks the proxy
        call itself.

        Every header under `{custom_header_prefix}` is captured into
        auth_info["custom_headers"] (keyed by the suffix after the prefix)
        unconditionally — this is a deliberately open-ended channel so new
        client-supplied attribution fields (e.g. from Claude Code's
        ANTHROPIC_CUSTOM_HEADERS) can be added later without a code change
        here. `{custom_header_prefix}user-id` additionally gets pulled out
        as auth_info["user_id"] as a best-effort, self-asserted fallback when
        there's no verified identity — recorded with auth_provider="custom-
        header" so it's never confused with OIDC-verified identity
        downstream. This is exactly as spoofable as the OIDC-gated headers
        above (any caller can set it); it's accepted anyway because this
        router is deployed per-user/local rather than as a shared
        multi-tenant ingress — there's no other caller who could spoof it
        against this instance. Re-gate this behind verification before
        deploying to a shared environment.
        """
        auth_info: dict[str, Any] = {}

        custom_headers = {
            k[len(self._custom_header_prefix) :]: v
            for k, v in request.headers.items()
            if k.lower().startswith(self._custom_header_prefix)
        }
        if custom_headers:
            auth_info["custom_headers"] = custom_headers

        verified_subject: str | None = None
        verified_email: str | None = None
        verified_user_name: str | None = None
        if self._token_reader is not None:
            auth_header = request.headers.get("authorization")
            token = (
                self._token_reader.extract_token(authorization_header=auth_header)
                if auth_header
                else None
            )
            if token:
                try:
                    token_item = await self._token_reader.verify_token_async(
                        token=token
                    )
                except (
                    AuthorizationBearerTokenExpiredException,
                    AuthorizationBearerTokenInvalidException,
                    ValueError,
                ) as e:
                    logger.warning(
                        "[coding-model-router] Authorization token failed validation "
                        "(%s); usage attribution disabled for this request.",
                        type(e).__name__,
                    )
                    token_item = None
                if token_item is not None:
                    verified_subject = token_item.subject or token_item.email
                    verified_email = token_item.email or (
                        token_item.subject
                        if token_item.subject and "@" in token_item.subject
                        else None
                    )
                    verified_user_name = token_item.name

        if verified_subject is None:
            # No verified identity — do not trust the OIDC-gated headers for
            # attribution, but do accept the operator-configured custom
            # header fallback (see docstring). The proxy call proceeds
            # regardless; only attribution is affected.
            if header_user_id := custom_headers.get("user-id"):
                auth_info["user_id"] = header_user_id
                auth_info["auth_provider"] = "custom-header"
            return auth_info

        auth_info["user_id"] = verified_subject
        if verified_email:
            auth_info["email"] = verified_email
        if verified_user_name:
            auth_info["user_name"] = verified_user_name
        if auth_provider := request.headers.get("x-auth-provider"):
            auth_info["auth_provider"] = auth_provider

        return auth_info
