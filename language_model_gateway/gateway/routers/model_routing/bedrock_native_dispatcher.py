"""
Dispatch mechanics for the native Bedrock Converse API transport
(bedrock_transport="native"), extracted from CodingModelRouter to keep
routing decisions separate from this transport's dispatch mechanics.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, cast

from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .aws_auth import _bedrock_credential_error_detail
from .bedrock_client import _pace_bedrock_dispatch, _throttle_backoff
from .bedrock_converse_client import (
    BedrockRuntimeClientProvider,
    _is_transient_bedrock_error_code,
)
from .constants import _MAX_THROTTLE_RETRIES
from .converse_request_translator import (
    _converse_response_to_anthropic,
    _openai_to_converse_request,
)
from .converse_stream_adapter import (
    _converse_stream_with_usage_tracking,
    _iter_converse_stream_events,
    _stream_bedrock_converse_to_anthropic,
)
from .stream_converter import _msg_id

if TYPE_CHECKING:
    from .usage_tracker import UsageTracker

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))


class BedrockNativeDispatcher:
    """Dispatches auth="aws" requests through the native Bedrock Converse
    API (bedrock_transport="native") instead of Bedrock Mantle's
    OpenAI-compatible endpoint. Owns the boto3 client lookup, request/
    response translation, and retry/error handling for that path — kept
    out of CodingModelRouter to keep routing decisions separate from
    this transport's dispatch mechanics, mirroring the
    BaseChatCompletionsProvider adapter pattern used for other backends.
    """

    def __init__(
        self,
        *,
        client_provider: BedrockRuntimeClientProvider,
        get_usage_tracker: Callable[[], "UsageTracker | None"],
        record_error: Callable[..., None],
        record_upstream_latency: Callable[..., None],
        error_response: Callable[[str, str, bool], "JSONResponse | StreamingResponse"],
    ) -> None:
        self._client_provider = client_provider
        self._get_usage_tracker = get_usage_tracker
        self._record_error = record_error
        self._record_upstream_latency = record_upstream_latency
        self._error_response = error_response

    async def dispatch_nonstreaming(
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
        bedrock_client = self._client_provider.get_client(route)
        converse_kwargs, tool_name_map = _openai_to_converse_request(
            body_json, route["model"]
        )

        throttle_attempt = 0
        while True:
            await _pace_bedrock_dispatch()
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
            resp, msg_id, upstream_model, tool_name_map
        )
        response = JSONResponse(anthropic_response)
        usage_tracker = self._get_usage_tracker()
        if usage_tracker:
            usage = resp.get("usage", {})
            background_tasks.add_task(
                usage_tracker.record_usage,
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
                bedrock_transport="native",
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                streaming=False,
                compression_requested=accept_encoding,
                compression_used="none",
                custom_headers=auth_info.get("custom_headers"),
                prompt_text=prompt_text,
                response_text=None,
                raw_usage=usage,
                retry_count=throttle_attempt,
            )
        response.background = background_tasks
        return response

    async def dispatch_streaming(
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
        request: Request,
        request_id: str,
        auth_info: dict[str, Any],
        request_start_time: datetime,
        dispatch_start: float,
    ) -> StreamingResponse | JSONResponse:
        """Streaming counterpart to dispatch_nonstreaming."""
        from botocore.exceptions import (
            ClientError,
            NoCredentialsError,
            TokenRetrievalError,
        )

        msg_id = _msg_id()
        bedrock_client = self._client_provider.get_client(route)
        converse_kwargs, tool_name_map = _openai_to_converse_request(
            body_json, route["model"]
        )

        throttle_attempt = 0
        while True:
            await _pace_bedrock_dispatch()
            try:
                raw_response = await asyncio.to_thread(
                    bedrock_client.converse_stream, **converse_kwargs
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
                    streaming=True,
                )
                return self._error_response(message, upstream_model, True)
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
                        "[coding-model-router] request_id=%s native Bedrock stream "
                        "throttled (attempt %d/%d): backing off %.1fs code=%s",
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
                    streaming=True,
                )
                return self._error_response(
                    f"Bedrock error ({error_code}): {error_message_text}",
                    upstream_model,
                    True,
                )

        self._record_upstream_latency(
            dispatch_start,
            model_tier=model_tier,
            upstream_model=upstream_model,
            auth=auth,
            api_type=api_type,
        )

        events = _iter_converse_stream_events(raw_response["stream"])

        # Mirrors router.py's own _record_mid_stream_error closure for the
        # Mantle path — a failure raised after streaming has already started
        # is only ever shown inline to the client unless recorded here too.
        def _record_mid_stream_error(message: str) -> None:
            self._record_error(
                request_id=msg_id,
                auth_info=auth_info,
                model=upstream_model,
                error_type="bedrock_native_error",
                error_message=message,
                start_time=request_start_time,
                model_tier=model_tier,
                backend=backend,
                auth=auth,
                api_type=api_type,
                streaming=True,
            )

        usage_tracker = self._get_usage_tracker()
        if usage_tracker:
            stream_gen = _converse_stream_with_usage_tracking(
                events,
                msg_id,
                upstream_model,
                usage_tracker,
                auth_info,
                request_start_time,
                prompt_text=prompt_text,
                model_tier=model_tier,
                backend=backend,
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                compression_requested=accept_encoding,
                compression_used="none",
                request=request,
                on_stream_error=_record_mid_stream_error,
                tool_name_map=tool_name_map,
                retry_count=throttle_attempt,
            )
        else:
            stream_gen = _stream_bedrock_converse_to_anthropic(
                events,
                msg_id,
                upstream_model,
                request=request,
                on_stream_error=_record_mid_stream_error,
                tool_name_map=tool_name_map,
            )
        return StreamingResponse(
            stream_gen,
            status_code=200,
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )
