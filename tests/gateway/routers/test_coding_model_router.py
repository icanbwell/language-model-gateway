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

import json
from unittest.mock import patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from language_model_gateway.gateway.routers.model_routing import (
    CodingModelRouter,
    _ThinkingStripper,
    _anthropic_to_openai_request,
    _is_throttling,
    _openai_to_anthropic_response,
    _ROUTES,
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
    assert "api.anthropic.com" in str(intercepted[0].url)


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
