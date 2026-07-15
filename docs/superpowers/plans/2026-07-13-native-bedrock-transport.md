# Native Bedrock Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `haiku`/`sonnet`-tier traffic route through Bedrock's native Converse API instead of Bedrock Mantle, toggled by a single env var, so on-call can fall back off Mantle during an incident without any model or cost-profile change.

**Architecture:** A new `bedrock_converse_client.py` module wraps a cached `boto3` `bedrock-runtime` client (via `asyncio.to_thread`) and converts between the OpenAI-shaped request/response `router.py` already builds and Bedrock's Converse API shape. `router.py` gains one new dispatch branch, gated on `auth == "aws"` and a new `self._bedrock_transport == "native"` flag, that calls into this module instead of constructing an `openai.AsyncOpenAI` client. The flag is read via `LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport` and threaded through `api.py:create_app()` into `CodingModelRouter.__init__`, exactly like every other `model_routing_*` setting.

**Tech Stack:** Python 3.12, `boto3`/`botocore` (already a dependency), `asyncio.to_thread` (no new async AWS SDK dependency), pytest + `unittest.mock`.

## Global Constraints

- No new dependency — `boto3` is already used in `aws_auth.py`; `types-boto3-bedrock-runtime` is already a dev-only type-stub dependency (not runtime-importable in this environment; do not add a runtime import of `mypy_boto3_bedrock_runtime`, type boto3 client instances as `Any` instead, matching the existing convention in `aws_auth.py`).
- Same Qwen model IDs (`qwen.qwen3-coder-30b-a3b-v1:0`, `qwen.qwen3-coder-next`) on both transports — only the transport layer changes.
- No automatic failover and no per-route granularity — one global env var (`MODEL_ROUTING_BEDROCK_TRANSPORT`, default `"mantle"`), an operator-flipped static toggle.
- The Anthropic-facing wire contract (non-streaming response shape, streaming SSE event sequence) must be identical to the Mantle path regardless of transport.
- Mock only at the `boto3.client("bedrock-runtime")` boundary in tests — no real AWS calls in CI.
- **Deviation from the committed spec, discovered while grounding this plan:** the spec's `_anthropic_to_converse_request(body_json, model_id)` assumed the source is the raw Anthropic-format request. In the actual code, `router.py` converts `body_json` to OpenAI-Chat-Completions shape unconditionally whenever `api_type == "openai"` — via the tokenizer-based context-budget path when the route has a `tokenizer_model` (`router.py:300-303`), or via the character-based path otherwise (`router.py:359-361`) — and this conversion happens *before* the dispatch branch this plan adds is reached. Both haiku and sonnet routes have `tokenizer_model` set today, but the conversion isn't conditional on that — it happens for every `api_type == "openai"` route either way. Re-deriving the Converse request from the original Anthropic body would skip whichever budget enforcement ran. This plan therefore builds the Converse request from the **already-OpenAI-shaped, already-budget-enforced** `body_json` instead — function is named `_openai_to_converse_request`, not `_anthropic_to_converse_request`. Response conversion is unaffected (Converse's response is converted directly to Anthropic shape, same as the spec).
- **Scope reduction, explicitly noted (not silently dropped):** image content blocks (Anthropic `{"type": "image", ...}` → OpenAI `image_url` → Converse `image`) are not supported on the native path in this plan. `_openai_to_converse_request` drops them with a logged warning rather than crashing, matching the "forward compatibility, no crash on unhandled shapes" principle. Add support later if this router is used for image-bearing coding-agent traffic (it isn't known to be today).
- No dedicated test asserts that `api.py:create_app()` threads `bedrock_transport` through to `CodingModelRouter(...)` — no other `model_routing_*` constructor kwarg has such a test today either (checked: none exist), so this isn't a new gap introduced by this feature. The property itself is unit-tested directly (Task 1), and router-level tests (Tasks 7–8) construct `CodingModelRouter(bedrock_transport="native")` directly, matching the existing `router_client_with_trackers` fixture pattern.

---

### Task 1: Wire the `bedrock_transport` toggle end-to-end

**Files:**
- Modify: `language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py`
- Modify: `language_model_gateway/gateway/routers/model_routing/router.py:113-131` (constructor)
- Modify: `language_model_gateway/gateway/api.py:193-210` (`create_app()`)
- Test: `tests/gateway/utilities/test_language_model_gateway_environment_variables.py` (new file)
- Test: `tests/gateway/routers/test_coding_model_router.py`

**Interfaces:**
- Produces: `LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport -> str` (property, default `"mantle"`)
- Produces: `CodingModelRouter.__init__(..., bedrock_transport: str = "mantle")`, stored as `self._bedrock_transport: str`
- Consumed by: Tasks 7–8's dispatch branch (`if self._bedrock_transport == "native" and auth == "aws":`)

- [ ] **Step 1: Write the failing test for the new property**

Create `tests/gateway/utilities/test_language_model_gateway_environment_variables.py`:

```python
"""
Tests for LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport.
"""

from __future__ import annotations

import pytest

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


def test_model_routing_bedrock_transport_defaults_to_mantle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_TRANSPORT", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "mantle"


def test_model_routing_bedrock_transport_reads_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "native")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "native"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/utilities/test_language_model_gateway_environment_variables.py -q`
Expected: FAIL — `AttributeError: 'LanguageModelGatewayEnvironmentVariables' object has no attribute 'model_routing_bedrock_transport'`

- [ ] **Step 3: Add the property**

In `language_model_gateway_environment_variables.py`, add immediately after `model_routing_account_directory_collection_name` (the last `model_routing_*` property):

```python
    @property
    def model_routing_bedrock_transport(self) -> str:
        """Which transport CodingModelRouter uses for auth="aws" routes:
        "mantle" (default) sends requests through Bedrock Mantle's
        OpenAI-compatible endpoint; "native" sends them through Bedrock's
        own Converse API instead, using the same model IDs. A manual,
        operator-flipped fallback for Bedrock Mantle incidents — see
        docs/superpowers/specs/2026-07-13-native-bedrock-transport-design.md.
        """
        return os.environ.get("MODEL_ROUTING_BEDROCK_TRANSPORT", "mantle")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/utilities/test_language_model_gateway_environment_variables.py -q`
Expected: `2 passed`

- [ ] **Step 5: Thread it through `CodingModelRouter.__init__`**

In `router.py`, add the parameter to `__init__` (after `custom_header_prefix`):

```python
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
```

And inside the body, right after `self._custom_header_prefix: str = custom_header_prefix.lower()`:

```python
        self._bedrock_transport: str = bedrock_transport
```

- [ ] **Step 6: Write the failing test for constructor storage**

Add to `tests/gateway/routers/test_coding_model_router.py` (near the top-level tests, not inside a specific test class — this file has no test classes, just module-level functions):

```python
def test_bedrock_transport_defaults_to_mantle() -> None:
    router = CodingModelRouter()
    assert router._bedrock_transport == "mantle"


def test_bedrock_transport_stores_native_override() -> None:
    router = CodingModelRouter(bedrock_transport="native")
    assert router._bedrock_transport == "native"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k bedrock_transport`
Expected: FAIL — `AttributeError: 'CodingModelRouter' object has no attribute '_bedrock_transport'`

- [ ] **Step 8: Run test to verify it passes**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k bedrock_transport`
Expected: `2 passed`

- [ ] **Step 9: Thread it through `api.py:create_app()`**

In `api.py`, inside the `CodingModelRouter(...)` constructor call (around line 194-210), add one more kwarg, next to `error_collection_name`:

```python
            error_collection_name=env_vars.model_routing_error_collection_name,
            bedrock_transport=env_vars.model_routing_bedrock_transport,
```

- [ ] **Step 10: Run the full existing suite to confirm no regressions**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py tests/gateway/utilities/test_language_model_gateway_environment_variables.py -q`
Expected: all passing, no failures

- [ ] **Step 11: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py language_model_gateway/gateway/routers/model_routing/router.py language_model_gateway/gateway/api.py && ruff format --check language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py language_model_gateway/gateway/routers/model_routing/router.py language_model_gateway/gateway/api.py && mypy language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py language_model_gateway/gateway/routers/model_routing/router.py language_model_gateway/gateway/api.py"`
Expected: all clean

- [ ] **Step 12: Commit**

```bash
git add language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py \
        language_model_gateway/gateway/routers/model_routing/router.py \
        language_model_gateway/gateway/api.py \
        tests/gateway/utilities/test_language_model_gateway_environment_variables.py \
        tests/gateway/routers/test_coding_model_router.py
git commit -m "BAI-299 Add MODEL_ROUTING_BEDROCK_TRANSPORT toggle, unwired

Adds model_routing_bedrock_transport (default \"mantle\") and threads it
from api.py through CodingModelRouter's constructor as
self._bedrock_transport. No dispatch behavior changes yet — the flag
does nothing until later tasks add the native-Bedrock code path that
reads it."
```

---

### Task 2: `bedrock_converse_client.py` — boto3 client cache and error classification

**Files:**
- Create: `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`
- Test: `tests/gateway/routers/model_routing/test_bedrock_converse_client.py` (new file)

**Interfaces:**
- Consumes: `_bedrock_credential_error_detail` from `aws_auth.py` (existing, unchanged: `_bedrock_credential_error_detail(exc: BaseException) -> tuple[str, str] | None`)
- Produces: `_get_bedrock_runtime_client(route: dict[str, Any]) -> Any` (cached per `(profile, region)`)
- Produces: `_is_transient_bedrock_error_code(code: str | None) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`:

```python
"""
Tests for bedrock_converse_client.py's boto3 client cache and error
classification helpers.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _get_bedrock_runtime_client,
    _is_transient_bedrock_error_code,
)


class TestGetBedrockRuntimeClient:
    def test_creates_client_with_route_region(self) -> None:
        route = {"aws_region": "us-west-2"}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_client = MagicMock()
            mock_session_cls.return_value.client.return_value = mock_client

            result = _get_bedrock_runtime_client(route)

            assert result is mock_client
            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-west-2"
            )

    def test_defaults_region_to_us_east_1(self) -> None:
        route: dict[str, str] = {}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_session_cls.return_value.client.return_value = MagicMock()

            _get_bedrock_runtime_client(route)

            mock_session_cls.return_value.client.assert_called_once_with(
                "bedrock-runtime", region_name="us-east-1"
            )

    def test_reuses_cached_client_for_same_region(self) -> None:
        route = {"aws_region": "us-east-1"}
        with (
            patch(
                "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._CLIENT_CACHE",
                {},
            ),
            patch("boto3.Session") as mock_session_cls,
        ):
            mock_session_cls.return_value.client.return_value = MagicMock()

            first = _get_bedrock_runtime_client(route)
            second = _get_bedrock_runtime_client(route)

            assert first is second
            mock_session_cls.return_value.client.assert_called_once()


class TestIsTransientBedrockErrorCode:
    def test_throttling_exception_is_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ThrottlingException") is True

    def test_model_stream_error_exception_is_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ModelStreamErrorException") is True

    def test_validation_exception_is_not_transient(self) -> None:
        assert _is_transient_bedrock_error_code("ValidationException") is False

    def test_none_is_not_transient(self) -> None:
        assert _is_transient_bedrock_error_code(None) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named '...bedrock_converse_client'`

- [ ] **Step 3: Write the implementation**

Create `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`:

```python
"""
Native Bedrock Converse API transport — an alternative to Bedrock Mantle's
OpenAI-compatible endpoint for auth="aws" routes, toggled by
CodingModelRouter._bedrock_transport ("mantle" default / "native").

Kept separate from bedrock_client.py (httpx passthrough + retry helpers for
the Mantle/Anthropic-passthrough paths) and aws_auth.py (SigV4 signing,
credential-error mapping for those same paths) — this module owns the boto3
bedrock-runtime client and the Anthropic/OpenAI <-> Converse format
conversions, which are a distinct concern from either.
"""

from __future__ import annotations

import os
from typing import Any

from .bedrock_client import _TRANSIENT_STREAM_ERROR_CODES

_CLIENT_CACHE: dict[tuple[str | None, str], Any] = {}


def _get_bedrock_runtime_client(route: dict[str, Any]) -> Any:
    """Return a cached boto3 bedrock-runtime client for this route's
    (AWS_PROFILE, region) pair. boto3 clients are thread-safe and reusable,
    so one is built per pair, not per request — mirrors the credential
    resolution in aws_auth.py's _sign_bedrock, which also keys off
    AWS_PROFILE and the route's aws_region.
    """
    import boto3

    profile = os.environ.get("AWS_PROFILE")
    region = route.get("aws_region", "us-east-1")
    key = (profile, region)
    if key not in _CLIENT_CACHE:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        _CLIENT_CACHE[key] = session.client("bedrock-runtime", region_name=region)
    return _CLIENT_CACHE[key]


def _is_transient_bedrock_error_code(code: str | None) -> bool:
    """Whether a native Bedrock ClientError's Error.Code is worth retrying
    with backoff — reuses the same exception-name taxonomy already applied
    to Bedrock Mantle's mid-stream errors in bedrock_client.py, since these
    are the same underlying Bedrock exception names either way.
    """
    return code in _TRANSIENT_STREAM_ERROR_CODES
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: `7 passed`

- [ ] **Step 5: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && ruff format --check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && mypy language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py"`
Expected: all clean

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py \
        tests/gateway/routers/model_routing/test_bedrock_converse_client.py
git commit -m "BAI-299 Add cached boto3 bedrock-runtime client for native transport

_get_bedrock_runtime_client caches one client per (AWS_PROFILE, region)
pair rather than building one per request. _is_transient_bedrock_error_code
reuses bedrock_client.py's existing Bedrock exception-name taxonomy for
retry decisions on the native path."
```

---

### Task 3: Request conversion — `_openai_to_converse_request`

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`
- Test: `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`

**Interfaces:**
- Consumes: nothing new — operates on the OpenAI-Chat-Completions-shaped `dict` that `message_translator.py:_anthropic_to_openai_request` already produces (see its docstring/tests for the exact shape: `messages` with `role`/`content`/`tool_calls`/`tool_call_id`, `tools`, `tool_choice`, `max_tokens`, `temperature`, `top_p`)
- Produces: `_openai_to_converse_request(oai_body_json: dict[str, Any], model_id: str) -> dict[str, Any]` — kwargs ready to splat into `client.converse(**kwargs)` / `client.converse_stream(**kwargs)`

- [ ] **Step 1: Write the failing tests**

Add to `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`:

```python
from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _openai_to_converse_request,
)


class TestOpenaiToConverseRequest:
    def test_plain_text_conversation(self) -> None:
        oai_body = {
            "model": "qwen.qwen3-coder-next",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024,
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["modelId"] == "qwen.qwen3-coder-next"
        assert result["messages"] == [
            {"role": "user", "content": [{"text": "Hello"}]}
        ]
        assert result["inferenceConfig"] == {"maxTokens": 1024}
        assert "system" not in result
        assert "toolConfig" not in result

    def test_system_prompt_becomes_system_field(self) -> None:
        oai_body = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["system"] == [{"text": "You are a helpful assistant."}]
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hi"}]}]

    def test_assistant_tool_call_becomes_tool_use_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Boston"}',
                            },
                        }
                    ],
                },
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assistant_msg = result["messages"][1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == [
            {
                "toolUse": {
                    "toolUseId": "call_1",
                    "name": "get_weather",
                    "input": {"city": "Boston"},
                }
            }
        ]

    def test_tool_result_becomes_user_turn_tool_result_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "72F, sunny"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        tool_result_msg = result["messages"][2]
        assert tool_result_msg == {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "call_1",
                        "content": [{"text": "72F, sunny"}],
                    }
                }
            ],
        }

    def test_tools_and_tool_choice_become_tool_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        },
                    },
                }
            ],
            "tool_choice": "auto",
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["tools"] == [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        }
                    },
                }
            }
        ]
        assert result["toolConfig"]["toolChoice"] == {"auto": {}}

    def test_specific_tool_choice_maps_to_named_tool(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "get_weather", "parameters": {}},
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["toolChoice"] == {"tool": {"name": "get_weather"}}

    def test_multi_turn_conversation_preserves_order(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Second question"},
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert [m["role"] for m in result["messages"]] == ["user", "assistant", "user"]
        assert result["messages"][0]["content"] == [{"text": "First question"}]
        assert result["messages"][1]["content"] == [{"text": "First answer"}]
        assert result["messages"][2]["content"] == [{"text": "Second question"}]

    def test_image_url_content_block_is_dropped_not_crashed(self) -> None:
        oai_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,abc123"},
                        },
                    ],
                }
            ],
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["messages"][0]["content"] == [
            {"text": "What's in this image?"}
        ]

    def test_temperature_and_top_p_map_to_inference_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        result = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["inferenceConfig"] == {"temperature": 0.7, "topP": 0.9}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q -k ConverseRequest`
Expected: FAIL — `ImportError: cannot import name '_openai_to_converse_request'`

- [ ] **Step 3: Write the implementation**

Add to `bedrock_converse_client.py` (add `import json` and `import logging` to the top imports, plus the module logger):

```python
import json
import logging
import os
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .bedrock_client import _TRANSIENT_STREAM_ERROR_CODES

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_CLIENT_CACHE: dict[tuple[str | None, str], Any] = {}
```

(This replaces the earlier bare `import os` / `from typing import Any` header from Task 2 — the logger is new, added here since this is the first function that needs it.)

Then add the conversion function:

```python
def _openai_to_converse_request(
    oai_body_json: dict[str, Any], model_id: str
) -> dict[str, Any]:
    """Translate an OpenAI-Chat-Completions-shaped request body (as produced
    by message_translator.py's _anthropic_to_openai_request, and already run
    through context-budget enforcement by the time router.py reaches the
    native-Bedrock dispatch branch) into kwargs for boto3's
    bedrock-runtime.converse / .converse_stream.

    Deliberately converts from the OpenAI shape, not the original Anthropic
    request — see the "Deviation from the committed spec" note in this
    plan/module for why: budget enforcement already ran on the OpenAI shape
    upstream of this call, and re-deriving from Anthropic would skip it.
    """
    converse: dict[str, Any] = {"modelId": model_id}

    messages: list[dict[str, Any]] = []
    system: list[dict[str, str]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def _flush_tool_results() -> None:
        if pending_tool_results:
            messages.append(
                {"role": "user", "content": list(pending_tool_results)}
            )
            pending_tool_results.clear()

    for msg in oai_body_json.get("messages", []):
        role = msg.get("role")
        if role == "system":
            system.append({"text": msg.get("content") or ""})
            continue
        if role == "tool":
            pending_tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": msg.get("tool_call_id", ""),
                        "content": [{"text": msg.get("content") or ""}],
                    }
                }
            )
            continue
        _flush_tool_results()
        if role == "assistant":
            content: list[dict[str, Any]] = []
            if text := msg.get("content"):
                content.append({"text": text})
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                try:
                    tool_input = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "input": tool_input,
                        }
                    }
                )
            messages.append({"role": "assistant", "content": content})
        elif role == "user":
            content_field = msg.get("content")
            if isinstance(content_field, str):
                messages.append(
                    {"role": "user", "content": [{"text": content_field}]}
                )
            elif isinstance(content_field, list):
                blocks: list[dict[str, Any]] = []
                for block in content_field:
                    block_type = block.get("type")
                    if block_type == "text":
                        blocks.append({"text": block.get("text", "")})
                    elif block_type == "image_url":
                        logger.warning(
                            "[bedrock-converse] dropping image content block — "
                            "native Bedrock transport does not support image "
                            "input yet"
                        )
                    # Unknown block types are silently skipped, not raised —
                    # forward-compatible with new Anthropic/OpenAI content
                    # block types this router doesn't know about yet.
                messages.append({"role": "user", "content": blocks})
    _flush_tool_results()

    converse["messages"] = messages
    if system:
        converse["system"] = system

    inference_config: dict[str, Any] = {}
    if "max_tokens" in oai_body_json:
        inference_config["maxTokens"] = oai_body_json["max_tokens"]
    if "temperature" in oai_body_json:
        inference_config["temperature"] = oai_body_json["temperature"]
    if "top_p" in oai_body_json:
        inference_config["topP"] = oai_body_json["top_p"]
    if inference_config:
        converse["inferenceConfig"] = inference_config

    if tools := oai_body_json.get("tools"):
        tool_config: dict[str, Any] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "inputSchema": {
                            "json": t["function"].get("parameters", {})
                        },
                    }
                }
                for t in tools
            ]
        }
        tool_choice = oai_body_json.get("tool_choice")
        if tool_choice == "auto":
            tool_config["toolChoice"] = {"auto": {}}
        elif tool_choice == "required":
            tool_config["toolChoice"] = {"any": {}}
        elif isinstance(tool_choice, dict):
            tool_config["toolChoice"] = {
                "tool": {"name": tool_choice.get("function", {}).get("name", "")}
            }
        converse["toolConfig"] = tool_config

    return converse
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: `16 passed` (7 from Task 2 + 9 new)

- [ ] **Step 5: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && ruff format --check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && mypy language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py"`
Expected: all clean

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py \
        tests/gateway/routers/model_routing/test_bedrock_converse_client.py
git commit -m "BAI-299 Convert OpenAI-shaped requests to Bedrock Converse format

_openai_to_converse_request builds converse()/converse_stream() kwargs
from the already-OpenAI-shaped, already-budget-enforced request body
router.py produces today — not from the original Anthropic request, since
context-budget enforcement runs upstream of the native-transport dispatch
point and only understands the OpenAI shape. Covers text, tool_use/
tool_result round-trips, system prompts, and tool_choice mapping; image
content blocks are dropped with a warning rather than supported."
```

---

### Task 4: Non-streaming response conversion — `_converse_response_to_anthropic`

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`
- Test: `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`

**Interfaces:**
- Produces: `_converse_response_to_anthropic(resp: dict[str, Any], msg_id: str, upstream_model: str) -> dict[str, Any]` — same output shape as `message_translator.py:_openai_to_anthropic_response`
- Produces: `_CONVERSE_TO_ANT_STOP: dict[str, str]` (module constant, also reused by Task 5's streaming translator)

- [ ] **Step 1: Write the failing tests**

Add to `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`:

```python
from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _converse_response_to_anthropic,
)


class TestConverseResponseToAnthropic:
    def test_plain_text_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Hello there"}],
                }
            },
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["id"] == "msg_abc"
        assert result["type"] == "message"
        assert result["role"] == "assistant"
        assert result["content"] == [{"type": "text", "text": "Hello there"}]
        assert result["model"] == "qwen.qwen3-coder-next"
        assert result["stop_reason"] == "end_turn"
        assert result["stop_sequence"] is None
        assert result["usage"] == {"input_tokens": 10, "output_tokens": 5}

    def test_tool_use_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {"city": "Boston"},
                            }
                        }
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 20, "outputTokens": 8, "totalTokens": 28},
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["content"] == [
            {
                "type": "tool_use",
                "id": "tooluse_1",
                "name": "get_weather",
                "input": {"city": "Boston"},
            }
        ]
        assert result["stop_reason"] == "tool_use"

    def test_mixed_text_and_tool_use_content(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check that for you."},
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {},
                            }
                        },
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["content"] == [
            {"type": "text", "text": "Let me check that for you."},
            {"type": "tool_use", "id": "tooluse_1", "name": "get_weather", "input": {}},
        ]

    def test_max_tokens_stop_reason_maps_directly(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "max_tokens",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["stop_reason"] == "max_tokens"

    def test_unknown_stop_reason_defaults_to_end_turn(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "guardrail_intervened",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["stop_reason"] == "end_turn"

    def test_missing_usage_defaults_to_zero(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "hi"}]}},
            "stopReason": "end_turn",
        }
        result = _converse_response_to_anthropic(resp, "msg_abc", "qwen.qwen3-coder-next")
        assert result["usage"] == {"input_tokens": 0, "output_tokens": 0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q -k ConverseResponseToAnthropic`
Expected: FAIL — `ImportError: cannot import name '_converse_response_to_anthropic'`

- [ ] **Step 3: Write the implementation**

Add to `bedrock_converse_client.py`:

```python
# Converse's stopReason values that have a direct Anthropic equivalent.
# guardrail_intervened/content_filtered have no Anthropic counterpart —
# they fall through to the "end_turn" default below, matching the
# "no exhaustive enum switch without a default" rule for forward
# compatibility with stop reasons this router doesn't know about yet.
_CONVERSE_TO_ANT_STOP = {
    "end_turn": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "stop_sequence": "stop_sequence",
}


def _converse_response_to_anthropic(
    resp: dict[str, Any], msg_id: str, upstream_model: str
) -> dict[str, Any]:
    """Translate a non-streaming Bedrock Converse response to Anthropic
    Messages format — the Converse-API counterpart to
    message_translator.py's _openai_to_anthropic_response.
    """
    content: list[dict[str, Any]] = []
    message = resp.get("output", {}).get("message", {})
    for block in message.get("content", []):
        if "text" in block:
            content.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_use.get("toolUseId", ""),
                    "name": tool_use.get("name", ""),
                    "input": tool_use.get("input", {}),
                }
            )

    stop_reason = _CONVERSE_TO_ANT_STOP.get(resp.get("stopReason", ""), "end_turn")
    usage = resp.get("usage", {})

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": upstream_model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: `22 passed`

- [ ] **Step 5: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && ruff format --check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && mypy language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py"`
Expected: all clean

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py \
        tests/gateway/routers/model_routing/test_bedrock_converse_client.py
git commit -m "BAI-299 Convert non-streaming Converse responses to Anthropic format

_converse_response_to_anthropic mirrors _openai_to_anthropic_response's
contract for the native transport. stopReason values without a direct
Anthropic equivalent (guardrail_intervened, content_filtered) default to
end_turn rather than raising on an unrecognized value."
```

---

### Task 5: Streaming adapter and event translator

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`
- Test: `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`

**Interfaces:**
- Consumes: `_sse_event` from `stream_converter.py` (existing: `_sse_event(event_type: str, data: dict[str, Any]) -> bytes`)
- Consumes: `_CONVERSE_TO_ANT_STOP` from Task 4
- Produces: `_iter_converse_stream_events(sync_events: Any) -> AsyncGenerator[dict[str, Any], None]`
- Produces: `_stream_bedrock_converse_to_anthropic(events: AsyncGenerator[dict[str, Any], None], msg_id: str, upstream_model: str, usage_sink: dict[str, int] | None = None, text_sink: dict[str, str] | None = None, request: Request | None = None, on_stream_error: Callable[[str], None] | None = None) -> AsyncGenerator[bytes, None]` — same external contract as `stream_converter.py:_stream_oai_sdk_to_anthropic`

- [ ] **Step 1: Write the failing tests**

Add to `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`:

```python
import asyncio

import pytest

from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _iter_converse_stream_events,
    _stream_bedrock_converse_to_anthropic,
)


class FakeSyncEventStream:
    """Stands in for boto3's synchronous EventStream — a plain iterator."""

    def __init__(self, events: list[dict]) -> None:
        self._iter = iter(events)

    def __iter__(self) -> "FakeSyncEventStream":
        return self

    def __next__(self) -> dict:
        return next(self._iter)


class FakeSyncEventStreamThatRaises:
    def __init__(self, events: list[dict], exc: Exception) -> None:
        self._iter = iter(events)
        self._exc = exc

    def __iter__(self) -> "FakeSyncEventStreamThatRaises":
        return self

    def __next__(self) -> dict:
        try:
            return next(self._iter)
        except StopIteration:
            raise self._exc from None


class TestIterConverseStreamEvents:
    @pytest.mark.asyncio
    async def test_yields_events_in_order(self) -> None:
        events = [{"messageStart": {"role": "assistant"}}, {"messageStop": {"stopReason": "end_turn"}}]
        sync_stream = FakeSyncEventStream(events)
        result = [e async for e in _iter_converse_stream_events(sync_stream)]
        assert result == events

    @pytest.mark.asyncio
    async def test_propagates_exception_mid_stream(self) -> None:
        events = [{"messageStart": {"role": "assistant"}}]
        sync_stream = FakeSyncEventStreamThatRaises(events, RuntimeError("boom"))
        collected = []
        with pytest.raises(RuntimeError, match="boom"):
            async for e in _iter_converse_stream_events(sync_stream):
                collected.append(e)
        assert collected == events


class TestStreamBedrockConverseToAnthropic:
    @staticmethod
    async def _fake_events(events: list[dict]):
        for e in events:
            yield e

    @pytest.mark.asyncio
    async def test_text_only_stream_emits_expected_sse_sequence(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Hello"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 3, "outputTokens": 2}}},
            ]
        )
        usage_sink: dict[str, int] = {}
        text_sink: dict[str, str] = {}
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                usage_sink=usage_sink,
                text_sink=text_sink,
            )
        ]
        joined = b"".join(chunks).decode()
        assert "event: message_start" in joined
        assert "event: content_block_start" in joined
        assert '"type": "text"' in joined
        assert "event: content_block_delta" in joined
        assert '"text": "Hello"' in joined
        assert "event: content_block_stop" in joined
        assert "event: message_delta" in joined
        assert "event: message_stop" in joined
        assert usage_sink == {"input_tokens": 3, "output_tokens": 2}
        assert text_sink == {"output_text": "Hello"}

    @pytest.mark.asyncio
    async def test_tool_use_stream_emits_tool_use_block(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {
                    "contentBlockStart": {
                        "contentBlockIndex": 0,
                        "start": {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                            }
                        },
                    }
                },
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"toolUse": {"input": '{"city": "Boston"}'}},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "tool_use"}},
                {"metadata": {"usage": {"inputTokens": 5, "outputTokens": 4}}},
            ]
        )
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                events, "msg_abc", "qwen.qwen3-coder-next"
            )
        ]
        joined = b"".join(chunks).decode()
        assert '"type": "tool_use"' in joined
        assert '"id": "tooluse_1"' in joined
        assert '"name": "get_weather"' in joined
        assert "input_json_delta" in joined
        assert '"partial_json": "{\\"city\\": \\"Boston\\"}"' in joined
        assert '"stop_reason": "tool_use"' in joined

    @pytest.mark.asyncio
    async def test_mid_stream_error_invokes_on_stream_error(self) -> None:
        async def _raising_events():
            yield {"messageStart": {"role": "assistant"}}
            raise RuntimeError("bedrock stream failed")

        captured: list[str] = []
        chunks = [
            c
            async for c in _stream_bedrock_converse_to_anthropic(
                _raising_events(),
                "msg_abc",
                "qwen.qwen3-coder-next",
                on_stream_error=captured.append,
            )
        ]
        assert captured == ["bedrock stream failed"]
        joined = b"".join(chunks).decode()
        assert "message_stop" in joined
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q -k "IterConverseStreamEvents or StreamBedrockConverseToAnthropic"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

Add to `bedrock_converse_client.py` (add these imports to the top: `import asyncio`, `from typing import Any, AsyncGenerator, Callable`, `from starlette.requests import Request`, and `from .stream_converter import _sse_event`):

```python
async def _iter_converse_stream_events(sync_events: Any) -> AsyncGenerator[dict[str, Any], None]:
    """Adapt boto3's synchronous converse_stream() EventStream onto the
    asyncio event loop — pulling one event at a time via asyncio.to_thread,
    since boto3 has no native async client and iterating its EventStream
    blocks the thread it's called from.
    """
    iterator = iter(sync_events)
    while True:
        try:
            event = await asyncio.to_thread(next, iterator)
        except StopIteration:
            return
        yield event


async def _stream_bedrock_converse_to_anthropic(
    events: AsyncGenerator[dict[str, Any], None],
    msg_id: str,
    upstream_model: str,
    usage_sink: dict[str, int] | None = None,
    text_sink: dict[str, str] | None = None,
    request: Request | None = None,
    on_stream_error: Callable[[str], None] | None = None,
) -> AsyncGenerator[bytes, None]:
    """Convert a Bedrock Converse event stream to Anthropic SSE format —
    the Converse-API counterpart to
    stream_converter.py:_stream_oai_sdk_to_anthropic. Same external
    contract (sinks, on_stream_error hook, emitted SSE event sequence) so
    it plugs into the existing usage-tracking/cleanup wrapper pattern
    without changes to that pattern itself.
    """
    if usage_sink is None:
        usage_sink = {}
    usage_sink["input_tokens"] = 0
    usage_sink["output_tokens"] = 0
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
                idx = event["contentBlockStart"]["contentBlockIndex"]
                start = event["contentBlockStart"].get("start") or {}
                if "toolUse" in start:
                    tool_use = start["toolUse"]
                    open_block_types[idx] = "tool_use"
                    yield _sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": idx,
                            "content_block": {
                                "type": "tool_use",
                                "id": tool_use.get("toolUseId", ""),
                                "name": tool_use.get("name", ""),
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
                if "inputTokens" in usage:
                    usage_sink["input_tokens"] = usage["inputTokens"]
                if "outputTokens" in usage:
                    usage_sink["output_tokens"] = usage["outputTokens"]
    except Exception as exc:
        logger.error("[bedrock-converse] upstream stream error: %s", exc)
        stream_error_msg = str(exc)
        if on_stream_error is not None:
            on_stream_error(stream_error_msg)

    for idx in sorted(open_block_types):
        yield _sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": idx}
        )

    yield _sse_event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": usage_sink["output_tokens"]},
        },
    )
    yield _sse_event("message_stop", {"type": "message_stop"})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: `27 passed`

- [ ] **Step 5: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && ruff format --check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && mypy language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py"`
Expected: all clean

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py \
        tests/gateway/routers/model_routing/test_bedrock_converse_client.py
git commit -m "BAI-299 Add async adapter and SSE translator for Converse streaming

_iter_converse_stream_events pulls boto3's synchronous EventStream onto
the event loop via asyncio.to_thread, one event per thread hop.
_stream_bedrock_converse_to_anthropic translates Converse stream events
into the same Anthropic SSE sequence _stream_oai_sdk_to_anthropic already
emits for the Mantle path, with the same sinks/on_stream_error contract."
```

---

### Task 6: Usage-tracking streaming wrapper

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py`
- Test: `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`

**Interfaces:**
- Consumes: `_fire_and_forget` from `stream_converter.py` (existing)
- Produces: `_converse_stream_with_usage_tracking(events: AsyncGenerator[dict[str, Any], None], msg_id: str, upstream_model: str, usage_tracker: Any, auth_info: dict[str, Any], start_time: datetime, *, prompt_text: str | None = None, model_tier: str | None = None, backend: str | None = None, price_per_mtok: float | None = None, anthropic_price_per_mtok: float | None = None, compression_requested: str | None = None, compression_used: str | None = None, request: Request | None = None, on_stream_error: Callable[[str], None] | None = None) -> AsyncGenerator[bytes, None]`

- [ ] **Step 1: Write the failing test**

Add to `tests/gateway/routers/model_routing/test_bedrock_converse_client.py`:

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from language_model_gateway.gateway.routers.model_routing.bedrock_converse_client import (
    _converse_stream_with_usage_tracking,
)

_TEST_START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestConverseStreamWithUsageTracking:
    @staticmethod
    async def _fake_events(events: list[dict]):
        for e in events:
            yield e

    @pytest.mark.asyncio
    async def test_records_usage_after_stream_completes(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Hi"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 7, "outputTokens": 3}}},
            ]
        )
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()
        auth_info = {"user_id": "user-1", "session_id": "sess-1"}

        chunks = [
            c
            async for c in _converse_stream_with_usage_tracking(
                events,
                "msg_abc",
                "qwen.qwen3-coder-next",
                usage_tracker,
                auth_info,
                _TEST_START_TIME,
                model_tier="sonnet",
                backend="aws_bedrock",
            )
        ]
        assert b"".join(chunks)  # something was yielded

        await asyncio.sleep(0)  # let the fire-and-forget task run
        usage_tracker.record_usage.assert_awaited_once()
        call_kwargs = usage_tracker.record_usage.call_args.kwargs
        assert call_kwargs["request_id"] == "msg_abc"
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["model"] == "qwen.qwen3-coder-next"
        assert call_kwargs["input_tokens"] == 7
        assert call_kwargs["output_tokens"] == 3
        assert call_kwargs["model_tier"] == "sonnet"
        assert call_kwargs["backend"] == "aws_bedrock"
        assert call_kwargs["streaming"] is True
        assert call_kwargs["response_text"] == "Hi"

    @pytest.mark.asyncio
    async def test_skips_recording_when_no_tokens_used(self) -> None:
        events = self._fake_events(
            [
                {"messageStart": {"role": "assistant"}},
                {"messageStop": {"stopReason": "end_turn"}},
            ]
        )
        usage_tracker = MagicMock()
        usage_tracker.record_usage = AsyncMock()

        _ = [
            c
            async for c in _converse_stream_with_usage_tracking(
                events, "msg_abc", "qwen.qwen3-coder-next", usage_tracker, {}, _TEST_START_TIME
            )
        ]
        await asyncio.sleep(0)
        usage_tracker.record_usage.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q -k ConverseStreamWithUsageTracking`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

Add to `bedrock_converse_client.py` (add `from datetime import datetime` to imports, and `from .stream_converter import _fire_and_forget, _sse_event`):

```python
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
) -> AsyncGenerator[bytes, None]:
    """Stream wrapper that records usage to MongoDB after the stream
    completes — the Converse-API counterpart to
    stream_converter.py:_oai_stream_with_usage_tracking. No httpx client to
    close here (boto3 manages its own connection pooling internally), so
    this is simpler than its OAI counterpart — just the sink bookkeeping
    and the record_usage call.
    """
    usage_sink: dict[str, int] = {}
    text_sink: dict[str, str] = {}
    async for chunk in _stream_bedrock_converse_to_anthropic(
        events,
        msg_id,
        upstream_model,
        usage_sink=usage_sink,
        text_sink=text_sink,
        request=request,
        on_stream_error=on_stream_error,
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
                price_per_mtok=price_per_mtok,
                anthropic_price_per_mtok=anthropic_price_per_mtok,
                streaming=True,
                compression_requested=compression_requested,
                compression_used=compression_used,
                custom_headers=auth_info.get("custom_headers"),
                prompt_text=prompt_text,
                response_text=text_sink.get("output_text"),
                start_time=start_time,
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/model_routing/test_bedrock_converse_client.py -q`
Expected: `29 passed`

- [ ] **Step 5: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && ruff format --check language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py && mypy language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py"`
Expected: all clean

- [ ] **Step 6: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/bedrock_converse_client.py \
        tests/gateway/routers/model_routing/test_bedrock_converse_client.py
git commit -m "BAI-299 Add usage-tracking wrapper for Converse streaming

_converse_stream_with_usage_tracking records usage via the generic
UsageTracker.record_usage (not the OpenAI-specific
record_usage_from_openai_response, since Converse's usage keys differ
from OpenAI's) after the stream completes, matching the skip-when-no-
tokens behavior of its OAI counterpart."
```

---

### Task 7: Router wiring — non-streaming dispatch

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/router.py`
- Test: `tests/gateway/routers/test_coding_model_router.py`

**Interfaces:**
- Consumes: `_get_bedrock_runtime_client`, `_openai_to_converse_request`, `_converse_response_to_anthropic`, `_is_transient_bedrock_error_code` from `bedrock_converse_client.py`
- Consumes: `_bedrock_credential_error_detail` from `aws_auth.py`, `_throttle_backoff` from `bedrock_client.py`
- Produces: `CodingModelRouter._dispatch_bedrock_native_nonstreaming(...)` — called from the new dispatch branch added in this task

- [ ] **Step 1: Write the failing tests**

Add to `tests/gateway/routers/test_coding_model_router.py`. Needs two import changes at the top of the file: add `from botocore.exceptions import ClientError`, and change the existing `from typing import AsyncGenerator` to `from typing import Any, AsyncGenerator` (the new fixture below is annotated `dict[str, Any]`, and `Any` isn't currently imported in this file).

```python
@pytest.fixture
def native_bedrock_route() -> dict[str, Any]:
    return {
        "tier": "sonnet",
        "claude_model": "claude-test-native-sonnet",
        "url": "https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions",
        "model": "qwen.qwen3-coder-next",
        "auth": "aws",
        "aws_region": "us-east-1",
        "api_type": "openai",
        "price_per_mtok": 0.5,
        "anthropic_price_per_mtok": 3.0,
    }


@pytest.mark.asyncio
async def test_native_bedrock_nonstreaming_happy_path(
    native_bedrock_route: dict[str, Any],
) -> None:
    """When bedrock_transport="native" and the route's auth is "aws", a
    non-streaming request must go through the Converse API, not Mantle's
    openai.AsyncOpenAI client."""
    router = CodingModelRouter(bedrock_transport="native")
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {"message": {"role": "assistant", "content": [{"text": "Hi there"}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 5, "outputTokens": 3, "totalTokens": 8},
    }

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            }
            response = await client.post(
                "/v1/messages",
                json=body,
                headers={"content-type": "application/json"},
            )

    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["content"] == [{"type": "text", "text": "Hi there"}]
    assert resp_json["stop_reason"] == "end_turn"
    mock_client.converse.assert_called_once()
    call_kwargs = mock_client.converse.call_args.kwargs
    assert call_kwargs["modelId"] == "qwen.qwen3-coder-next"


@pytest.mark.asyncio
async def test_native_bedrock_mantle_default_transport_unaffected(
    native_bedrock_route: dict[str, Any],
) -> None:
    """With bedrock_transport left at its "mantle" default, an auth="aws"
    route must still go through the openai SDK path — the native branch
    must not be reachable without the explicit toggle."""
    router = CodingModelRouter()  # default bedrock_transport="mantle"
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            }
            # No httpx_mock response registered for the openai SDK's target
            # URL, so this will fail to connect — that's fine, we're only
            # asserting the native client was never touched.
            try:
                await client.post(
                    "/v1/messages",
                    json=body,
                    headers={"content-type": "application/json"},
                )
            except Exception:
                pass

    mock_client.converse.assert_not_called()


@pytest.mark.asyncio
async def test_native_bedrock_nonstreaming_records_usage(
    native_bedrock_route: dict[str, Any],
) -> None:
    router = CodingModelRouter(bedrock_transport="native")
    usage_tracker = MagicMock()
    usage_tracker.record_usage = AsyncMock()
    router._usage_tracker = usage_tracker
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {"message": {"role": "assistant", "content": [{"text": "Hi"}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 5, "outputTokens": 3, "totalTokens": 8},
    }

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            }
            await client.post(
                "/v1/messages", json=body, headers={"content-type": "application/json"}
            )

    await asyncio.sleep(0)
    usage_tracker.record_usage.assert_awaited_once()
    call_kwargs = usage_tracker.record_usage.call_args.kwargs
    assert call_kwargs["input_tokens"] == 5
    assert call_kwargs["output_tokens"] == 3
    assert call_kwargs["streaming"] is False


@pytest.mark.asyncio
async def test_native_bedrock_nonstreaming_client_error_is_recorded(
    native_bedrock_route: dict[str, Any],
) -> None:
    """A non-transient ClientError (e.g. ValidationException) must be
    recorded via _record_error with error_type="bedrock_native_error" and
    the AWS request ID from the ClientError response metadata."""
    router = CodingModelRouter(bedrock_transport="native")
    usage_tracker = MagicMock()
    usage_tracker.record_usage = AsyncMock()
    error_tracker = MagicMock()
    error_tracker.record_error = AsyncMock()
    router._usage_tracker = usage_tracker
    router._error_tracker = error_tracker
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse.side_effect = ClientError(
        {
            "Error": {"Code": "ValidationException", "Message": "bad request"},
            "ResponseMetadata": {"RequestId": "aws-req-123"},
        },
        "Converse",
    )

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            }
            response = await client.post(
                "/v1/messages", json=body, headers={"content-type": "application/json"}
            )

    assert response.status_code == 200  # errors surfaced as a 200 assistant message
    await asyncio.sleep(0)
    error_tracker.record_error.assert_awaited_once()
    call_kwargs = error_tracker.record_error.call_args.kwargs
    assert call_kwargs["error_type"] == "bedrock_native_error"
    recorded = json.loads(call_kwargs["error_message"])
    assert recorded["code"] == "ValidationException"
    assert recorded["request_id"] == "aws-req-123"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k native_bedrock`
Expected: FAIL — requests fall through to the (non-existent, unmocked) Mantle openai path and error out with connection/httpx-mock failures, since the native dispatch branch doesn't exist yet

- [ ] **Step 3: Write the implementation**

In `router.py`, add the new imports (near the existing `.bedrock_client` import block):

```python
from .bedrock_converse_client import (
    _converse_response_to_anthropic,
    _get_bedrock_runtime_client,
    _is_transient_bedrock_error_code,
    _openai_to_converse_request,
)
```

Add the dispatch branch right at the top of the `if api_type == "openai":` block (`router.py:440`), before `import openai`:

```python
        # ── Native Bedrock Converse route: manual fallback for Bedrock Mantle ──
        if api_type == "openai" and auth == "aws" and self._bedrock_transport == "native":
            if is_streaming:
                return await self._dispatch_bedrock_native_streaming(
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
```

(`_dispatch_bedrock_native_streaming` is added in Task 8 — this task only defines `_dispatch_bedrock_native_nonstreaming` and will leave the streaming branch's target method to fail with `AttributeError` until Task 8, which is fine since no test in this task exercises `is_streaming=True`.)

Add the new method to the `CodingModelRouter` class, near `_handle_unexpected_upstream_error` (same indentation level, i.e. a regular instance method):

```python
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
        from botocore.exceptions import ClientError, NoCredentialsError, TokenRetrievalError

        msg_id = _msg_id()
        bedrock_client = _get_bedrock_runtime_client(route)
        converse_kwargs = _openai_to_converse_request(body_json, route["model"])

        throttle_attempt = 0
        while True:
            try:
                resp = await asyncio.to_thread(bedrock_client.converse, **converse_kwargs)
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
                return self._error_response(message, upstream_model, False)
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
                return self._error_response(
                    f"Bedrock error ({error_code}): {error_message_text}",
                    upstream_model,
                    False,
                )

        self._record_upstream_latency(
            dispatch_start,
            model_tier=model_tier,
            upstream_model=upstream_model,
            auth=auth,
            api_type=api_type,
        )
        anthropic_response = _converse_response_to_anthropic(resp, msg_id, upstream_model)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k native_bedrock`
Expected: `4 passed` (happy path, mantle-unaffected, usage recording, ClientError recording — `test_native_bedrock_mantle_default_transport_unaffected` also counts)

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py tests/gateway/routers/model_routing/ -q`
Expected: all passing

- [ ] **Step 6: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/router.py tests/gateway/routers/test_coding_model_router.py && ruff format --check language_model_gateway/gateway/routers/model_routing/router.py tests/gateway/routers/test_coding_model_router.py && mypy language_model_gateway/gateway/routers/model_routing/router.py"`
Expected: all clean

- [ ] **Step 7: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/router.py \
        tests/gateway/routers/test_coding_model_router.py
git commit -m "BAI-299 Wire non-streaming native Bedrock dispatch into router.py

Adds the auth==\"aws\" && bedrock_transport==\"native\" branch ahead of
the existing openai-SDK Mantle path, and
_dispatch_bedrock_native_nonstreaming to handle it: converse() via
asyncio.to_thread, throttle-retry on transient ClientError codes,
credential-error and non-transient-error recording via the existing
_record_error/_error_response helpers with error_type=\"bedrock_native_error\".
Streaming requests still fall through to a not-yet-implemented method,
completed in the next task."
```

---

### Task 8: Router wiring — streaming dispatch

**Files:**
- Modify: `language_model_gateway/gateway/routers/model_routing/router.py`
- Test: `tests/gateway/routers/test_coding_model_router.py`

**Interfaces:**
- Consumes: `_iter_converse_stream_events`, `_converse_stream_with_usage_tracking`, `_stream_bedrock_converse_to_anthropic` from `bedrock_converse_client.py` (Tasks 5–6)
- Produces: `CodingModelRouter._dispatch_bedrock_native_streaming(...)`

- [ ] **Step 1: Write the failing tests**

Add to `tests/gateway/routers/test_coding_model_router.py`:

```python
@pytest.mark.asyncio
async def test_native_bedrock_streaming_happy_path(
    native_bedrock_route: dict[str, Any],
) -> None:
    router = CodingModelRouter(bedrock_transport="native")
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse_stream.return_value = {
        "stream": iter(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "Streamed hi"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 4, "outputTokens": 2}}},
            ]
        )
    }

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            }
            response = await client.post(
                "/v1/messages",
                json=body,
                headers={"content-type": "application/json"},
            )

    assert response.status_code == 200
    assert b"Streamed hi" in response.content
    assert b"event: message_start" in response.content
    assert b"event: message_stop" in response.content
    mock_client.converse_stream.assert_called_once()


@pytest.mark.asyncio
async def test_native_bedrock_streaming_records_usage(
    native_bedrock_route: dict[str, Any],
) -> None:
    router = CodingModelRouter(bedrock_transport="native")
    usage_tracker = MagicMock()
    usage_tracker.record_usage = AsyncMock()
    router._usage_tracker = usage_tracker
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse_stream.return_value = {
        "stream": iter(
            [
                {"messageStart": {"role": "assistant"}},
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": 0,
                        "delta": {"text": "hi"},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 4, "outputTokens": 2}}},
            ]
        )
    }

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            }
            await client.post(
                "/v1/messages", json=body, headers={"content-type": "application/json"}
            )

    await asyncio.sleep(0)
    usage_tracker.record_usage.assert_awaited_once()
    call_kwargs = usage_tracker.record_usage.call_args.kwargs
    assert call_kwargs["input_tokens"] == 4
    assert call_kwargs["output_tokens"] == 2
    assert call_kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_native_bedrock_streaming_mid_stream_error_is_recorded(
    native_bedrock_route: dict[str, Any],
) -> None:
    """A failure raised mid-iteration of converse_stream()'s EventStream
    (after streaming has already started, so it can't become a clean
    pre-first-chunk error response) must still reach model-router-errors —
    mirroring test_bedrock_mantle_mid_stream_error_records_full_detail for
    the Mantle path."""

    def _raising_stream():
        yield {"messageStart": {"role": "assistant"}}
        raise RuntimeError("native bedrock stream failed")

    router = CodingModelRouter(bedrock_transport="native")
    error_tracker = MagicMock()
    error_tracker.record_error = AsyncMock()
    router._error_tracker = error_tracker
    app = FastAPI()
    app.include_router(router.get_router())

    mock_client = MagicMock()
    mock_client.converse_stream.return_value = {"stream": _raising_stream()}

    with (
        patch.dict(_ROUTES, {"claude-test-native-sonnet": native_bedrock_route}),
        patch(
            "language_model_gateway.gateway.routers.model_routing.bedrock_converse_client._get_bedrock_runtime_client",
            return_value=mock_client,
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = {
                "model": "claude-test-native-sonnet",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            }
            response = await client.post(
                "/v1/messages", json=body, headers={"content-type": "application/json"}
            )

    assert response.status_code == 200
    await asyncio.sleep(0)
    error_tracker.record_error.assert_awaited_once()
    call_kwargs = error_tracker.record_error.call_args.kwargs
    assert call_kwargs["error_type"] == "bedrock_native_error"
    assert "native bedrock stream failed" in call_kwargs["error_message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k "native_bedrock_streaming"`
Expected: FAIL — `AttributeError: 'CodingModelRouter' object has no attribute '_dispatch_bedrock_native_streaming'`

- [ ] **Step 3: Write the implementation**

Add the new imports to `router.py` (extend the existing `.bedrock_converse_client` import block from Task 7):

```python
from .bedrock_converse_client import (
    _converse_response_to_anthropic,
    _converse_stream_with_usage_tracking,
    _get_bedrock_runtime_client,
    _is_transient_bedrock_error_code,
    _iter_converse_stream_events,
    _openai_to_converse_request,
    _stream_bedrock_converse_to_anthropic,
)
```

Add the new method next to `_dispatch_bedrock_native_nonstreaming`:

```python
    async def _dispatch_bedrock_native_streaming(
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
        """Streaming counterpart to _dispatch_bedrock_native_nonstreaming."""
        from botocore.exceptions import ClientError, NoCredentialsError, TokenRetrievalError

        msg_id = _msg_id()
        bedrock_client = _get_bedrock_runtime_client(route)
        converse_kwargs = _openai_to_converse_request(body_json, route["model"])

        throttle_attempt = 0
        while True:
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

        if self._usage_tracker:
            stream_gen = _converse_stream_with_usage_tracking(
                events,
                msg_id,
                upstream_model,
                self._usage_tracker,
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
            )
        else:
            stream_gen = _stream_bedrock_converse_to_anthropic(
                events,
                msg_id,
                upstream_model,
                request=request,
                on_stream_error=_record_mid_stream_error,
            )
        return StreamingResponse(
            stream_gen,
            status_code=200,
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py -q -k native_bedrock`
Expected: `7 passed` (4 from Task 7 + 3 new)

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `docker compose run --rm language-model-gateway pytest tests/gateway/routers/test_coding_model_router.py tests/gateway/routers/model_routing/ tests/gateway/utilities/test_language_model_gateway_environment_variables.py -q`
Expected: all passing

- [ ] **Step 6: Lint and typecheck**

Run: `docker compose run --rm language-model-gateway sh -c "ruff check language_model_gateway/gateway/routers/model_routing/router.py tests/gateway/routers/test_coding_model_router.py && ruff format --check language_model_gateway/gateway/routers/model_routing/router.py tests/gateway/routers/test_coding_model_router.py && mypy language_model_gateway/gateway/routers/model_routing/router.py"`
Expected: all clean

- [ ] **Step 7: Commit**

```bash
git add language_model_gateway/gateway/routers/model_routing/router.py \
        tests/gateway/routers/test_coding_model_router.py
git commit -m "BAI-299 Wire streaming native Bedrock dispatch into router.py

_dispatch_bedrock_native_streaming mirrors the non-streaming dispatch's
retry/error-recording logic, then hands off to
_converse_stream_with_usage_tracking (or the bare translator when usage
tracking is disabled). Mid-stream failures — after the SSE response has
already started — are recorded the same way router.py's own
_record_mid_stream_error does for the Mantle path, so they reach
model-router-errors instead of only being shown inline to the client."
```

---

### Task 9: Enable the toggle in local dev

**Files:**
- Modify: `docker-compose.yml`

**Interfaces:** none — configuration only, the last piece needed for the original ask ("set env var in docker-compose.yml to use native bedrock") to actually do something.

- [ ] **Step 1: Add the env var**

In `docker-compose.yml`, add immediately after `MODEL_ROUTING_USAGE_CAPTURE_PREVIEWS: "true"` (line 158):

```yaml
      # Manual fallback for Bedrock Mantle incidents — routes haiku/sonnet
      # traffic through Bedrock's native Converse API instead of Mantle's
      # OpenAI-compatible endpoint, using the same Qwen model IDs. Flip back
      # to "mantle" (or remove this line) once Mantle recovers.
      MODEL_ROUTING_BEDROCK_TRANSPORT: native
```

- [ ] **Step 2: Validate the compose file**

Run: `docker compose config --quiet`
Expected: no output, exit code 0

- [ ] **Step 3: Smoke-test locally**

Run: `docker compose up -d language-model-gateway` then send a haiku/sonnet-tier request through the running gateway (e.g. via Claude Code pointed at it, or a manual `curl` to `/v1/messages` with `"model": "claude-sonnet-5"`) and confirm in the container logs that `_dispatch_bedrock_native_nonstreaming`/`_dispatch_bedrock_native_streaming` is reached (grep logs for `"native Bedrock"` — every warning-level log line in the new dispatch methods includes that phrase) rather than the Mantle path's `"-> BEDROCK"` log line.

This is also the point to run the **manual smoke test** called out in the spec's Testing section: confirm `qwen.qwen3-coder-30b-a3b-v1:0` and `qwen.qwen3-coder-next` are actually invocable via native Bedrock's Converse API in `us-east-1` with real AWS credentials — nothing in this plan's automated tests exercises real AWS, so this is the first point that would surface a model-not-available error.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "BAI-299 Enable native Bedrock transport in local dev docker-compose

Sets MODEL_ROUTING_BEDROCK_TRANSPORT=native so haiku/sonnet traffic now
routes through Bedrock's Converse API instead of Bedrock Mantle by
default in this compose file. Flip back to \"mantle\" (or delete the
line) once no longer needed."
```
