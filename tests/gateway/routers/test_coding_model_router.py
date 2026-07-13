"""
Unit and integration tests for CodingModelRouter.

Tests cover:
- Helper functions: _ThinkingStripper, _anthropic_to_openai_request,
  _openai_to_anthropic_response, _is_throttling
- Route registration
- Invalid JSON → 400
- count_tokens estimate for OpenAI api_type routes
- Passthrough to Anthropic direct (streaming + non-streaming)
- Unknown model fallback to Anthropic direct
- Error response helpers (streaming + non-streaming)
"""

import asyncio
import json
import re
import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from oidcauthlib.auth.exceptions.authorization_bearer_token_invalid_exception import (
    AuthorizationBearerTokenInvalidException,
)
from pytest_httpx import HTTPXMock
from starlette.requests import Request

from language_model_gateway.gateway.routers.model_routing.bedrock_client import (
    _is_throttling,
)
from language_model_gateway.gateway.routers.model_routing.message_translator import (
    _anthropic_to_openai_request,
    _openai_to_anthropic_response,
)
from language_model_gateway.gateway.routers.model_routing.route_config import _ROUTES
from language_model_gateway.gateway.routers.model_routing.router import (
    CodingModelRouter,
)
from language_model_gateway.gateway.routers.model_routing.stream_converter import (
    ThinkingStripper as _ThinkingStripper,
)


# ---------------------------------------------------------------------------
# _ThinkingStripper
# ---------------------------------------------------------------------------


def test_thinking_stripper_no_think_block() -> None:
    s = _ThinkingStripper()
    assert s.feed("Hello world") == "Hello world"
    assert s.flush() == ""


def test_thinking_stripper_strips_block() -> None:
    s = _ThinkingStripper()
    visible = s.feed("<think>internal reasoning</think>answer")
    assert "internal reasoning" not in visible
    assert "answer" in visible


def test_thinking_stripper_block_spanning_chunks() -> None:
    s = _ThinkingStripper()
    assert s.feed("<think>part") == ""
    assert s.feed(" one</think>visible") == "visible"
    assert s.flush() == ""


def test_thinking_stripper_partial_open_tag_held_back() -> None:
    s = _ThinkingStripper()
    result = s.feed("text<thi")
    assert result == "text"
    assert s.flush() == "<thi"


def test_thinking_stripper_flush_discards_open_block() -> None:
    s = _ThinkingStripper()
    s.feed("<think>never closed")
    assert s.flush() == ""


# ---------------------------------------------------------------------------
# _is_throttling
# ---------------------------------------------------------------------------


def test_is_throttling_429() -> None:
    assert _is_throttling(429) is True


def test_is_throttling_context_overflow_not_throttling() -> None:
    body = "input contains at least 200000 input tokens"
    assert _is_throttling(400, body) is False


def test_is_throttling_throttle_text_in_body() -> None:
    assert _is_throttling(503, "Too many requests, please try again later") is True


def test_is_throttling_clean_500() -> None:
    assert _is_throttling(500, "Internal Server Error") is False


# ---------------------------------------------------------------------------
# _anthropic_to_openai_request
# ---------------------------------------------------------------------------


def test_anthropic_to_openai_simple_user_message() -> None:
    body = {
        "model": "claude-sonnet-4-6",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100,
    }
    result = _anthropic_to_openai_request(body)
    assert result["model"] == "claude-sonnet-4-6"
    assert result["max_tokens"] == 100
    assert result["messages"] == [{"role": "user", "content": "Hello"}]


def test_anthropic_to_openai_system_prompt() -> None:
    body = {
        "model": "m",
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    result = _anthropic_to_openai_request(body)
    assert result["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert result["messages"][1]["role"] == "user"


def test_anthropic_to_openai_tool_use_in_assistant() -> None:
    body = {
        "model": "m",
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Using tool"},
                    {
                        "type": "tool_use",
                        "id": "tool_123",
                        "name": "search",
                        "input": {"query": "test"},
                    },
                ],
            }
        ],
    }
    result = _anthropic_to_openai_request(body)
    msg = result["messages"][0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "Using tool"
    assert len(msg["tool_calls"]) == 1
    assert msg["tool_calls"][0]["function"]["name"] == "search"


def test_anthropic_to_openai_tool_result_becomes_tool_role() -> None:
    body = {
        "model": "m",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_123",
                        "content": "search result",
                    }
                ],
            }
        ],
    }
    result = _anthropic_to_openai_request(body)
    msg = result["messages"][0]
    assert msg["role"] == "tool"
    assert msg["tool_call_id"] == "tool_123"
    assert msg["content"] == "search result"


def test_anthropic_to_openai_tools_translated() -> None:
    body = {
        "model": "m",
        "messages": [],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
    }
    result = _anthropic_to_openai_request(body)
    assert result["tools"][0]["type"] == "function"
    assert result["tools"][0]["function"]["name"] == "get_weather"
    assert result["tools"][0]["function"]["parameters"] == {
        "type": "object",
        "properties": {},
    }


# ---------------------------------------------------------------------------
# _openai_to_anthropic_response
# ---------------------------------------------------------------------------


def test_openai_to_anthropic_text_response() -> None:
    oai = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Hello there",
                    "tool_calls": None,
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    result = _openai_to_anthropic_response(oai, "msg_abc", "upstream-model")
    assert result["id"] == "msg_abc"
    assert result["type"] == "message"
    assert result["role"] == "assistant"
    assert result["model"] == "upstream-model"
    assert result["stop_reason"] == "end_turn"
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"] == "Hello there"
    assert result["usage"]["input_tokens"] == 10
    assert result["usage"]["output_tokens"] == 5


def test_openai_to_anthropic_strips_think_blocks() -> None:
    oai = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "<think>reasoning</think>Visible answer",
                    "tool_calls": None,
                },
            }
        ],
        "usage": {},
    }
    result = _openai_to_anthropic_response(oai, "msg_x", "m")
    assert result["content"][0]["text"] == "Visible answer"


def test_openai_to_anthropic_tool_call_response() -> None:
    oai = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "search",
                                "arguments": '{"query": "test"}',
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {},
    }
    result = _openai_to_anthropic_response(oai, "msg_y", "m")
    assert result["stop_reason"] == "tool_use"
    tool_block = result["content"][0]
    assert tool_block["type"] == "tool_use"
    assert tool_block["name"] == "search"
    assert tool_block["input"] == {"query": "test"}


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_coding_model_router_registers_messages_route() -> None:
    from fastapi.routing import APIRoute

    router = CodingModelRouter()
    paths = {r.path for r in router.get_router().routes if isinstance(r, APIRoute)}
    assert "/v1/messages" in paths
    assert "/v1/messages/count_tokens" in paths


# ---------------------------------------------------------------------------
# _get_auth_info — usage-tracking identity validation
#
# x-openwebui-user-id/x-customer-id/etc. headers are fully caller-controlled,
# so they must never be trusted for usage-tracking attribution unless the
# Authorization header verifies as a genuine, signature-checked OIDC token.
# ---------------------------------------------------------------------------


def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_auth_info_no_token_reader_ignores_identity_headers() -> None:
    """Without a token_reader configured, identity headers must not be trusted."""
    router = CodingModelRouter()
    request = _make_request({"x-openwebui-user-id": "victim@example.com"})

    auth_info = await router._get_auth_info(request)

    assert "user_id" not in auth_info


@pytest.mark.asyncio
async def test_get_auth_info_no_authorization_header_ignores_identity_headers() -> None:
    """No Authorization header at all means no verified identity."""
    token_reader = MagicMock()
    router = CodingModelRouter(token_reader=token_reader)
    request = _make_request({"x-openwebui-user-id": "victim@example.com"})

    auth_info = await router._get_auth_info(request)

    assert "user_id" not in auth_info
    token_reader.verify_token_async.assert_not_called()


@pytest.mark.asyncio
async def test_get_auth_info_invalid_token_ignores_identity_headers() -> None:
    """An Authorization header that fails verification must not fall back to
    trusting caller-controlled identity headers (this is the IDOR closed by
    this fix — a spoofed/opaque Bearer value must not grant attribution)."""
    token_reader = MagicMock()
    token_reader.extract_token.return_value = "not-a-real-jwt"
    token_reader.verify_token_async = AsyncMock(
        side_effect=AuthorizationBearerTokenInvalidException(
            message="bad token", token="not-a-real-jwt"
        )
    )
    router = CodingModelRouter(token_reader=token_reader)
    request = _make_request(
        {
            "authorization": "Bearer not-a-real-jwt",
            "x-openwebui-user-id": "victim@example.com",
        }
    )

    auth_info = await router._get_auth_info(request)

    assert "user_id" not in auth_info


@pytest.mark.asyncio
async def test_get_auth_info_valid_token_uses_verified_identity_not_headers() -> None:
    """A verified token's claims are used for attribution, taking precedence
    over (and ignoring) any caller-supplied identity headers."""
    verified_token = MagicMock()
    verified_token.subject = "verified-user-123"
    verified_token.email = "verified@example.com"
    verified_token.name = "Verified User"

    token_reader = MagicMock()
    token_reader.extract_token.return_value = "a.valid.jwt"
    token_reader.verify_token_async = AsyncMock(return_value=verified_token)
    router = CodingModelRouter(token_reader=token_reader)
    request = _make_request(
        {
            "authorization": "Bearer a.valid.jwt",
            "x-openwebui-user-id": "attacker-supplied-id",
            "x-auth-provider": "okta",
        }
    )

    auth_info = await router._get_auth_info(request)

    assert auth_info["user_id"] == "verified-user-123"
    assert auth_info["email"] == "verified@example.com"
    assert auth_info["user_name"] == "Verified User"
    assert auth_info["auth_provider"] == "okta"


@pytest.mark.asyncio
async def test_get_auth_info_falls_back_to_custom_header_when_unverified() -> None:
    """With no verified identity, the operator-configured custom header wins."""
    router = CodingModelRouter(custom_header_prefix="x-bwell-")
    request = _make_request({"x-bwell-user-id": "imran.qureshi@bwell.com"})

    auth_info = await router._get_auth_info(request)

    assert auth_info["user_id"] == "imran.qureshi@bwell.com"
    assert auth_info["auth_provider"] == "custom-header"


@pytest.mark.asyncio
async def test_get_auth_info_verified_identity_wins_over_custom_header() -> None:
    """A verified OIDC identity still takes precedence over the custom header."""
    verified_token = MagicMock()
    verified_token.subject = "verified-user-123"
    verified_token.email = None
    verified_token.name = None

    token_reader = MagicMock()
    token_reader.extract_token.return_value = "a.valid.jwt"
    token_reader.verify_token_async = AsyncMock(return_value=verified_token)
    router = CodingModelRouter(
        token_reader=token_reader, custom_header_prefix="x-bwell-"
    )
    request = _make_request(
        {
            "authorization": "Bearer a.valid.jwt",
            "x-bwell-user-id": "someone-else@bwell.com",
        }
    )

    auth_info = await router._get_auth_info(request)

    assert auth_info["user_id"] == "verified-user-123"


@pytest.mark.asyncio
async def test_get_auth_info_no_custom_header_present() -> None:
    """No fallback header present means no user_id, same as before."""
    router = CodingModelRouter(custom_header_prefix="x-bwell-")
    request = _make_request({})

    auth_info = await router._get_auth_info(request)

    assert "user_id" not in auth_info


@pytest.mark.asyncio
async def test_get_auth_info_captures_all_prefixed_headers() -> None:
    """Any header under the prefix is captured, not just user-id — new
    attribution headers can be added later without a code change here."""
    router = CodingModelRouter(custom_header_prefix="x-bwell-")
    request = _make_request(
        {
            "x-bwell-user-id": "imran.qureshi@bwell.com",
            "x-bwell-project": "language-model-gateway",
            "x-openwebui-user-id": "not-under-our-prefix",
        }
    )

    auth_info = await router._get_auth_info(request)

    assert auth_info["custom_headers"] == {
        "user-id": "imran.qureshi@bwell.com",
        "project": "language-model-gateway",
    }


@pytest.mark.asyncio
async def test_get_auth_info_no_custom_headers_key_when_none_present() -> None:
    router = CodingModelRouter(custom_header_prefix="x-bwell-")
    request = _make_request({"authorization": "Bearer irrelevant"})

    auth_info = await router._get_auth_info(request)

    assert "custom_headers" not in auth_info


# ---------------------------------------------------------------------------
# _attach_account_uuid — records Claude Code's account_uuid on auth_info,
# unresolved (email resolution now happens downstream in reporting).
# ---------------------------------------------------------------------------


def test_attach_account_uuid_sets_it_from_body_metadata() -> None:
    """Should record account_uuid on auth_info when present in request metadata."""
    router = CodingModelRouter()

    auth_info: dict[str, object] = {}
    body_json = {
        "metadata": {
            "user_id": '{"account_uuid": "acct-123", "device_id": "d", "session_id": "s"}'
        }
    }

    router._attach_account_uuid(auth_info, body_json)

    assert auth_info["account_uuid"] == "acct-123"
    assert "user_id" not in auth_info
    assert "email" not in auth_info


def test_attach_account_uuid_does_not_override_verified_identity() -> None:
    """Should leave a pre-existing user_id alone — this never resolves identity."""
    router = CodingModelRouter()

    auth_info: dict[str, object] = {"user_id": "verified-subject"}
    body_json = {"metadata": {"user_id": '{"account_uuid": "acct-123"}'}}

    router._attach_account_uuid(auth_info, body_json)

    assert auth_info["user_id"] == "verified-subject"
    assert auth_info["account_uuid"] == "acct-123"


def test_attach_account_uuid_noop_when_account_uuid_missing() -> None:
    """Should be a no-op when the request body has no extractable account_uuid."""
    router = CodingModelRouter()

    auth_info: dict[str, object] = {}
    body_json: dict[str, object] = {}

    router._attach_account_uuid(auth_info, body_json)

    assert auth_info == {}


# ---------------------------------------------------------------------------
# _attach_claude_code_headers — session_id from the documented
# x-claude-code-session-id header (preferred), agent_id/parent_agent_id for
# subagent cost attribution.
# ---------------------------------------------------------------------------


def test_attach_claude_code_headers_prefers_session_header_over_body_metadata() -> None:
    router = CodingModelRouter()
    auth_info: dict[str, object] = {}
    request = _make_request({"x-claude-code-session-id": "sess-from-header"})
    body_json = {"metadata": {"user_id": '{"session_id": "sess-from-body"}'}}

    router._attach_claude_code_headers(auth_info, request, body_json)

    assert auth_info["session_id"] == "sess-from-header"


def test_attach_claude_code_headers_falls_back_to_body_metadata() -> None:
    """No x-claude-code-session-id header: fall back to the body blob."""
    router = CodingModelRouter()
    auth_info: dict[str, object] = {}
    request = _make_request({})
    body_json = {"metadata": {"user_id": '{"session_id": "sess-from-body"}'}}

    router._attach_claude_code_headers(auth_info, request, body_json)

    assert auth_info["session_id"] == "sess-from-body"


def test_attach_claude_code_headers_captures_agent_ids() -> None:
    router = CodingModelRouter()
    auth_info: dict[str, object] = {}
    request = _make_request(
        {
            "x-claude-code-session-id": "sess-1",
            "x-claude-code-agent-id": "agent-1",
            "x-claude-code-parent-agent-id": "agent-0",
        }
    )

    router._attach_claude_code_headers(auth_info, request, {})

    assert auth_info["agent_id"] == "agent-1"
    assert auth_info["parent_agent_id"] == "agent-0"


def test_attach_claude_code_headers_omits_agent_ids_when_absent() -> None:
    """A main-session request (not a subagent) carries no agent-id headers."""
    router = CodingModelRouter()
    auth_info: dict[str, object] = {}
    request = _make_request({"x-claude-code-session-id": "sess-1"})

    router._attach_claude_code_headers(auth_info, request, {})

    assert "agent_id" not in auth_info
    assert "parent_agent_id" not in auth_info


# ---------------------------------------------------------------------------
# _record_upstream_latency — model_tier latency visibility (Groundcover)
# ---------------------------------------------------------------------------


def test_record_upstream_latency_sets_span_attributes() -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("test-span"):
        dispatch_start = time.perf_counter() - 0.05  # simulate 50ms elapsed
        CodingModelRouter._record_upstream_latency(
            dispatch_start,
            model_tier="sonnet",
            upstream_model="claude-sonnet-4-6",
            auth="passthrough",
            api_type="anthropic",
        )

    (span,) = exporter.get_finished_spans()
    attributes = span.attributes
    assert attributes is not None
    assert attributes["model_tier"] == "sonnet"
    assert attributes["upstream_model"] == "claude-sonnet-4-6"
    assert attributes["auth_strategy"] == "passthrough"
    assert attributes["api_type"] == "anthropic"
    latency_ms = attributes["upstream_latency_ms"]
    assert isinstance(latency_ms, (int, float)) and latency_ms >= 50


def test_record_upstream_latency_noop_without_active_span() -> None:
    """With no active span (e.g. tracing disabled), this must not raise —
    OpenTelemetry's no-op span silently absorbs set_attribute calls."""
    dispatch_start = time.perf_counter()
    CodingModelRouter._record_upstream_latency(
        dispatch_start,
        model_tier="haiku",
        upstream_model="claude-haiku-4-5",
        auth="aws",
        api_type="openai",
    )


# ---------------------------------------------------------------------------
# Integration tests via ASGI client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_json_returns_400(router_client: httpx.AsyncClient) -> None:
    response = await router_client.post(
        "/v1/messages",
        content=b"not valid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert "invalid JSON body" in response.text


@pytest.mark.asyncio
async def test_count_tokens_openai_route_returns_estimate(
    router_client: httpx.AsyncClient,
) -> None:
    fake_route = {
        "claude_model": "claude-test-model",
        "url": "https://example.bedrock.aws/v1/chat/completions",
        "model": "upstream-model",
        "auth": "aws",
        "api_type": "openai",
    }
    with patch.dict(_ROUTES, {"claude-test-model": fake_route}):
        body = {
            "model": "claude-test-model",
            "messages": [{"role": "user", "content": "hello"}],
        }
        response = await router_client.post(
            "/v1/messages/count_tokens",
            json=body,
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "input_tokens" in data
    assert isinstance(data["input_tokens"], int)
    assert data["input_tokens"] > 0


@pytest.mark.asyncio
async def test_passthrough_unknown_model_calls_anthropic(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    upstream_body = json.dumps(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hi"}],
            "model": "claude-unknown",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 5, "output_tokens": 2},
        }
    ).encode()

    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=upstream_body,
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "claude-unknown-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = await router_client.post(
        "/v1/messages",
        json=body,
        headers={
            "content-type": "application/json",
            "authorization": "Bearer test-key",
        },
    )
    assert response.status_code == 200
    intercepted = httpx_mock.get_requests()
    assert len(intercepted) == 1
    assert str(intercepted[0].url).startswith("https://api.anthropic.com/v1/messages")


@pytest.mark.asyncio
async def test_passthrough_unknown_model_count_tokens(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    """Test that /count_tokens works for unknown models (falls back to Anthropic direct)."""
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages/count_tokens",
        method="POST",
        status_code=200,
        content=b'{"error": {"type": "unknown_model"}}',
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "claude-unknown-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = await router_client.post(
        "/v1/messages/count_tokens",
        json=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    intercepted = httpx_mock.get_requests()
    assert len(intercepted) == 1
    # Verify the URL is correct - the fallback should not double-append /count_tokens
    assert (
        str(intercepted[0].url) == "https://api.anthropic.com/v1/messages/count_tokens"
    )


@pytest.mark.asyncio
async def test_passthrough_route_forwards_auth_header(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    fake_route = {
        "claude_model": "claude-passthrough-test",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-passthrough-test",
        "auth": "passthrough",
    }
    upstream_body = json.dumps(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "response"}],
            "model": "claude-passthrough-test",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    ).encode()

    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=upstream_body,
        headers={"content-type": "application/json"},
    )

    with patch.dict(_ROUTES, {"claude-passthrough-test": fake_route}):
        body = {
            "model": "claude-passthrough-test",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = await router_client.post(
            "/v1/messages",
            json=body,
            headers={
                "content-type": "application/json",
                "authorization": "Bearer my-api-key",
            },
        )

    assert response.status_code == 200
    intercepted = httpx_mock.get_requests()
    assert len(intercepted) == 1
    forwarded_auth = intercepted[0].headers.get("authorization", "")
    assert forwarded_auth == "Bearer my-api-key"


@pytest.mark.asyncio
async def test_custom_header_prefix_stripped_before_forwarding_upstream(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    """Headers under the custom prefix are for local attribution only — never
    forwarded to the upstream Anthropic/Bedrock API."""
    fake_route = {
        "claude_model": "claude-passthrough-test",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-passthrough-test",
        "auth": "passthrough",
    }
    upstream_body = json.dumps(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "response"}],
            "model": "claude-passthrough-test",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    ).encode()

    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=upstream_body,
        headers={"content-type": "application/json"},
    )

    with patch.dict(_ROUTES, {"claude-passthrough-test": fake_route}):
        body = {
            "model": "claude-passthrough-test",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = await router_client.post(
            "/v1/messages",
            json=body,
            headers={
                "content-type": "application/json",
                "authorization": "Bearer my-api-key",
                "x-model-routing-user-id": "imran.qureshi@bwell.com",
            },
        )

    assert response.status_code == 200
    intercepted = httpx_mock.get_requests()
    assert len(intercepted) == 1
    assert "x-model-routing-user-id" not in intercepted[0].headers


@pytest.mark.asyncio
async def test_passthrough_forwards_clients_model_not_configured_model(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    """
    A passthrough route matched via claude_model_pattern (not the exact
    claude_model key) must forward the client's exact requested model id, not
    the pinned `model` value from config — Anthropic is authoritative on
    which model ids exist, so a stale pinned id must never silently override
    a newer one the client actually asked for.
    """
    fake_route = {
        "claude_model": "claude-opus-stale-pin",
        "claude_model_pattern": "^claude-opus-stale",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-opus-OLD-PINNED-ID",
        "auth": "passthrough",
    }
    upstream_body = json.dumps(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "ok"}],
            "model": "claude-opus-stale-pin-v2",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    ).encode()
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=upstream_body,
        headers={"content-type": "application/json"},
    )

    with patch(
        "language_model_gateway.gateway.routers.model_routing.route_config._PATTERNS",
        [(re.compile("^claude-opus-stale"), fake_route)],
    ):
        body = {
            "model": "claude-opus-stale-pin-v2",  # matches via pattern, not exact key
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = await router_client.post(
            "/v1/messages",
            json=body,
            headers={
                "content-type": "application/json",
                "authorization": "Bearer key",
            },
        )

    assert response.status_code == 200
    intercepted = httpx_mock.get_requests()
    sent_body = json.loads(intercepted[0].content)
    assert sent_body["model"] == "claude-opus-stale-pin-v2"


@pytest.mark.asyncio
async def test_upstream_error_propagated(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=401,
        content=b'{"error": {"message": "Unauthorized"}}',
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "unknown-model-triggers-fallback",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = await router_client.post(
        "/v1/messages",
        json=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unmatched_model_error_is_annotated_with_fallback_note(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    """
    When a model has no configured route, the request silently falls back to
    Anthropic direct with no cost-routing or context-budget enforcement. If
    that fallback request then errors upstream (e.g. context exceeded), the
    client must see *why* — not just the bare upstream error — so the
    confusing "context exceeded" symptom is traceable to the actual root
    cause (missing route config).
    """
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=400,
        content=b'{"error": {"message": "prompt is too long: 205000 tokens"}}',
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "claude-brand-new-tier-9",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = await router_client.post(
        "/v1/messages",
        json=body,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    error_message = response.json()["error"]["message"]
    assert "claude-brand-new-tier-9" in error_message
    assert "no configured route" in error_message
    assert "prompt is too long: 205000 tokens" in error_message


@pytest.mark.asyncio
async def test_matched_route_error_is_not_annotated(
    router_client: httpx.AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    """A route that *is* configured (not a fallback) must return the upstream
    error verbatim — the annotation is only for unmatched-model fallbacks."""
    fake_route = {
        "claude_model": "claude-configured-test",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-configured-test",
        "auth": "passthrough",
    }
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=401,
        content=b'{"error": {"message": "Unauthorized"}}',
        headers={"content-type": "application/json"},
    )

    with patch.dict(_ROUTES, {"claude-configured-test": fake_route}):
        body = {
            "model": "claude-configured-test",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = await router_client.post(
            "/v1/messages",
            json=body,
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 401
    assert response.json() == {"error": {"message": "Unauthorized"}}


# ---------------------------------------------------------------------------
# Anthropic-passthrough usage/error tracking (BAI-299)
# ---------------------------------------------------------------------------


@pytest.fixture
async def router_client_with_trackers() -> AsyncGenerator[
    tuple[httpx.AsyncClient, MagicMock, MagicMock], None
]:
    """Same shape as `router_client`, but with mocked usage/error trackers
    attached directly — avoids needing a real Mongo connection while still
    exercising the router's own wiring (which fields it passes, when).

    Returns the mocks themselves (not `router`) so callers assert against
    `UsageTracker`/`ErrorTracker`-shaped mocks rather than the `X | None`
    attribute type on CodingModelRouter.
    """
    router = CodingModelRouter()
    usage_tracker = MagicMock()
    usage_tracker.record_usage = AsyncMock()
    usage_tracker.record_usage_from_anthropic_response = AsyncMock()
    error_tracker = MagicMock()
    error_tracker.record_error = AsyncMock()
    router._usage_tracker = usage_tracker
    router._error_tracker = error_tracker
    app = FastAPI()
    app.include_router(router.get_router())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, usage_tracker, error_tracker


@pytest.mark.asyncio
async def test_anthropic_passthrough_non_streaming_records_usage(
    router_client_with_trackers: tuple[httpx.AsyncClient, MagicMock, MagicMock],
    httpx_mock: HTTPXMock,
) -> None:
    client, usage_tracker, error_tracker = router_client_with_trackers
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=json.dumps(
            {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi"}],
                "model": "claude-unknown",
                "usage": {"input_tokens": 5, "output_tokens": 2},
            }
        ).encode(),
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "claude-unknown-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = await client.post(
        "/v1/messages",
        json=body,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["usage"] == {"input_tokens": 5, "output_tokens": 2}
    usage_tracker.record_usage_from_anthropic_response.assert_awaited_once()
    call_kwargs = usage_tracker.record_usage_from_anthropic_response.call_args.kwargs
    assert call_kwargs["model"] == "claude-unknown-model-xyz"
    assert call_kwargs["streaming"] is False
    assert call_kwargs["response_body"]["usage"] == {
        "input_tokens": 5,
        "output_tokens": 2,
    }
    error_tracker.record_error.assert_not_awaited()


@pytest.mark.asyncio
async def test_anthropic_passthrough_streaming_relays_bytes_and_records_usage(
    router_client_with_trackers: tuple[httpx.AsyncClient, MagicMock, MagicMock],
    httpx_mock: HTTPXMock,
) -> None:
    client, usage_tracker, error_tracker = router_client_with_trackers
    sse_body = (
        b"event: message_start\n"
        b'data: {"type":"message_start","message":{"usage":{"input_tokens":9,"output_tokens":1}}}\n\n'
        b"event: content_block_delta\n"
        b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"hi"}}\n\n'
        b"event: message_delta\n"
        b'data: {"type":"message_delta","usage":{"output_tokens":4}}\n\n'
        b"event: message_stop\n"
        b'data: {"type":"message_stop"}\n\n'
    )
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=200,
        content=sse_body,
        headers={"content-type": "text/event-stream"},
    )

    body = {
        "model": "claude-unknown-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }
    response = await client.post(
        "/v1/messages",
        json=body,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.content == sse_body

    await asyncio.sleep(0)  # let the fire-and-forget usage-recording task run
    usage_tracker.record_usage.assert_awaited_once()
    call_kwargs = usage_tracker.record_usage.call_args.kwargs
    assert call_kwargs["model"] == "claude-unknown-model-xyz"
    assert call_kwargs["input_tokens"] == 9
    assert call_kwargs["output_tokens"] == 4
    assert call_kwargs["streaming"] is True
    error_tracker.record_error.assert_not_awaited()


@pytest.mark.asyncio
async def test_anthropic_passthrough_upstream_error_records_error(
    router_client_with_trackers: tuple[httpx.AsyncClient, MagicMock, MagicMock],
    httpx_mock: HTTPXMock,
) -> None:
    client, usage_tracker, error_tracker = router_client_with_trackers
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        method="POST",
        status_code=503,
        content=b'{"error": {"message": "overloaded"}}',
        headers={"content-type": "application/json"},
    )

    body = {
        "model": "claude-unknown-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = await client.post(
        "/v1/messages",
        json=body,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 503
    await asyncio.sleep(0)  # let the fire-and-forget error-recording task run
    error_tracker.record_error.assert_awaited_once()
    call_kwargs = error_tracker.record_error.call_args.kwargs
    assert call_kwargs["status_code"] == 503
    assert call_kwargs["error_type"] == "upstream_error"
    assert "overloaded" in call_kwargs["error_message"]
    usage_tracker.record_usage_from_anthropic_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_bedrock_mantle_mid_stream_error_records_full_detail(
    router_client_with_trackers: tuple[httpx.AsyncClient, MagicMock, MagicMock],
    httpx_mock: HTTPXMock,
) -> None:
    """Bedrock Mantle can send a `{"error": {...}}` SSE data event mid-stream
    instead of a 4xx/5xx HTTP response. The openai SDK raises a plain
    `openai.APIError` for this (no `.status_code`) — distinct from
    `openai.APIStatusError`. Before this fix, that fell through to the
    generic `except Exception` handler and only `str(exc)` (a generic
    message) reached model-router-errors. The `.body`/`.code`/`.type` detail
    the SDK actually attaches must now be captured."""
    client, usage_tracker, error_tracker = router_client_with_trackers
    fake_route = {
        "claude_model": "claude-test-model-oai",
        "url": "https://example.bedrock.aws/v1/chat/completions",
        "model": "qwen.qwen3-coder-next",
        "auth": "passthrough",
        "api_type": "openai",
    }
    sse_body = (
        b'data: {"error": {"message": "ModelStreamErrorException: model '
        b'timed out mid-stream", "code": "ModelStreamErrorException", '
        b'"type": "server_error"}}\n\n'
    )
    httpx_mock.add_response(
        url="https://example.bedrock.aws/v1/chat/completions",
        method="POST",
        status_code=200,
        content=sse_body,
        headers={"content-type": "text/event-stream"},
    )

    with patch.dict(_ROUTES, {"claude-test-model-oai": fake_route}):
        body = {
            "model": "claude-test-model-oai",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        }
        response = await client.post(
            "/v1/messages",
            json=body,
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 200
    assert b"ModelStreamErrorException: model timed out mid-stream" in response.content
    # The client (e.g. Claude Code) must see the same code/type detail that's
    # now captured in model-router-errors, not just the generic message.
    assert b"server_error" in response.content

    await asyncio.sleep(0)  # let the fire-and-forget error-recording task run
    error_tracker.record_error.assert_awaited_once()
    call_kwargs = error_tracker.record_error.call_args.kwargs
    assert call_kwargs["error_type"] == "bedrock_stream_error"
    recorded = json.loads(call_kwargs["error_message"])
    assert recorded["code"] == "ModelStreamErrorException"
    assert recorded["type"] == "server_error"
    assert "timed out mid-stream" in recorded["message"]
    assert recorded["body"]["code"] == "ModelStreamErrorException"
    usage_tracker.record_usage_from_openai_response.assert_not_called()
