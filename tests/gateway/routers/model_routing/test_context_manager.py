"""
Tests for context_manager.py.

No network calls — the tokenizer is mocked so these tests run without
downloading any HuggingFace model.
"""

from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import _patch, patch

from language_model_gateway.gateway.routers.model_routing.context_manager import (
    _TOOL_COMPRESS_THRESHOLD_CHARS,
    _TOOL_HEAD_CHARS,
    _TOOL_TAIL_CHARS,
    _TRUNCATION_MARKER,
    ContextBudget,
    build_budget,
    compress_tool_result_text,
    enforce_context_budget,
)

FAKE_MODEL = "test-tokenizer/does-not-exist"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _msg(role: str, content: str = "", **kw: object) -> dict[str, Any]:
    return {"role": role, "content": content, **kw}


def _tool_call_group(tool_call_id: str, result: str) -> list[dict[str, Any]]:
    """Atomic group: assistant tool-call + its tool response."""
    return [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": "bash", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": tool_call_id, "content": result},
    ]


def _body(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 8192,
) -> dict[str, Any]:
    b: dict[str, Any] = {"model": "m", "messages": messages, "max_tokens": max_tokens}
    if tools:
        b["tools"] = tools
    return b


def _mock_count(value: int | None) -> _patch:  # type: ignore[type-arg]
    """Patch count_oai_request_tokens to always return *value*."""
    return patch(
        "language_model_gateway.gateway.routers.model_routing.context_manager"
        ".count_oai_request_tokens",
        return_value=value,
    )


def _mock_count_seq(values: Sequence[int | None]) -> _patch:  # type: ignore[type-arg]
    """Patch count_oai_request_tokens to return successive values."""
    return patch(
        "language_model_gateway.gateway.routers.model_routing.context_manager"
        ".count_oai_request_tokens",
        side_effect=values,
    )


# ---------------------------------------------------------------------------
# ContextBudget
# ---------------------------------------------------------------------------


def test_budget_defaults() -> None:
    b = ContextBudget()
    assert b.backend_max_context_tokens == 262144
    assert b.reserved_output_tokens == 16384
    assert b.tokenizer_safety_margin == 6000
    assert b.effective_input_tokens == 262144 - 16384 - 6000


def test_build_budget_from_route() -> None:
    route = {
        "backend_max_context_tokens": 200000,
        "reserved_output_tokens": 20000,
        "tokenizer_safety_margin": 5000,
    }
    b = build_budget(route)
    assert b.backend_max_context_tokens == 200000
    assert b.reserved_output_tokens == 20000
    assert b.tokenizer_safety_margin == 5000
    assert b.effective_input_tokens == 175000


def test_build_budget_explicit_effective_input_tokens() -> None:
    """explicit effective_input_tokens back-computes backend_max_context_tokens."""
    route = {"effective_input_tokens": 240000}
    b = build_budget(route)
    assert b.effective_input_tokens == 240000


def test_build_budget_empty_route_uses_defaults() -> None:
    b = build_budget({})
    assert b == ContextBudget()


# ---------------------------------------------------------------------------
# compress_tool_result_text
# ---------------------------------------------------------------------------


def test_compress_short_text_unchanged() -> None:
    text = "short result"
    assert compress_tool_result_text(text) == text


def test_compress_long_text_structure() -> None:
    """Head and tail are preserved; middle replaced by marker."""
    head = "A" * _TOOL_HEAD_CHARS
    middle = "B" * 10000
    tail = "C" * _TOOL_TAIL_CHARS
    text = head + middle + tail
    result = compress_tool_result_text(text)
    assert result.startswith(head)
    assert result.endswith(tail)
    assert _TRUNCATION_MARKER in result


def test_compress_tail_preserved_for_stack_traces() -> None:
    """The end of command output (where errors live) must survive compression."""
    noise = "INFO: compiling...\n" * 500
    error_line = "FATAL: test_foo: AssertionError('expected 42, got 0')"
    text = noise + error_line
    compressed = compress_tool_result_text(text)
    assert error_line in compressed


def test_compress_uses_truncation_marker() -> None:
    big = "x" * 20000
    assert _TRUNCATION_MARKER in compress_tool_result_text(big)


def test_compress_tail_larger_than_head() -> None:
    """Tail chars > head chars so error tails are fully preserved."""
    assert _TOOL_TAIL_CHARS > _TOOL_HEAD_CHARS


# ---------------------------------------------------------------------------
# enforce_context_budget — fits without compression
# ---------------------------------------------------------------------------


def test_no_compression_when_under_budget() -> None:
    """Request well within budget → returned identical (same object or equal)."""
    messages = [_msg("system", "sys"), _msg("user", "hello")]
    body = _body(messages)
    with _mock_count(1000):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    assert result["messages"] == messages


# ---------------------------------------------------------------------------
# enforce_context_budget — tokenizer unavailable
# ---------------------------------------------------------------------------


def test_tokenizer_unavailable_small_body_passes_through() -> None:
    """Tiny body: char estimate is well under budget → returned unchanged."""
    body = _body([_msg("user", "hello")])
    with _mock_count(None):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    assert result is body


def test_char_estimate_fallback_compresses_when_over_budget() -> None:
    """
    When transformers is unavailable, char-estimate triggers Phase 1 compression.

    Budget is tuned so the initial char estimate exceeds it, but after tool-result
    head+tail compression the char estimate fits — so only Phase 1 runs, leaving
    the (compressed) tool message visible in the result.

    Initial body:  ~100 KB tool result → char-estimate ~25 000 tokens > budget 2 000
    After Phase 1: ~4 500 chars        → char-estimate ~1 100 tokens  < budget 2 000
    """
    route = {
        "backend_max_context_tokens": 10000,
        "reserved_output_tokens": 3000,
        "tokenizer_safety_margin": 5000,
    }
    # effective_input_tokens = 10000 - 3000 - 5000 = 2000
    big_tool = "X" * 100_000  # ensures initial char estimate >> 2000
    messages = [
        _msg("system", "sys"),
        *_tool_call_group("tc1", big_tool),
        _msg("user", "CURRENT"),
    ]
    body = _body(messages)
    # count_oai_request_tokens returns None → char estimate used for all recounts.
    with _mock_count(None):
        result = enforce_context_budget(body, route, FAKE_MODEL)
    tool_msg = next(m for m in result["messages"] if m.get("role") == "tool")
    assert _TRUNCATION_MARKER in tool_msg["content"]


# ---------------------------------------------------------------------------
# enforce_context_budget — phase 1: tool result compression
# ---------------------------------------------------------------------------


def test_oversized_tool_result_compressed() -> None:
    """A tool message larger than the threshold is head+tail compressed."""
    big = "Z" * (2 * _TOOL_COMPRESS_THRESHOLD_CHARS)
    messages = [
        _msg("system", "sys"),
        *_tool_call_group("tc1", big),
        _msg("user", "continue"),
    ]
    body = _body(messages)
    # First count: over budget. After tool compression: under budget.
    with _mock_count_seq([300000, 200000]):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    tool_msg = next(m for m in result["messages"] if m.get("role") == "tool")
    assert _TRUNCATION_MARKER in tool_msg["content"]
    assert len(tool_msg["content"]) < len(big)


def test_small_tool_result_not_compressed() -> None:
    """Tool results below the threshold pass through unchanged."""
    small = "output: ok"
    messages = [
        *_tool_call_group("tc1", small),
        _msg("user", "done"),
    ]
    body = _body(messages)
    # Under budget from the start → no compression at all.
    with _mock_count(1000):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    tool_msg = next(m for m in result["messages"] if m.get("role") == "tool")
    assert tool_msg["content"] == small


# ---------------------------------------------------------------------------
# enforce_context_budget — phase 2: drop oldest groups
# ---------------------------------------------------------------------------


def test_drops_oldest_groups_when_compression_insufficient() -> None:
    """When tool compression alone doesn't fit, oldest groups are dropped."""
    messages = [
        _msg("system", "sys"),
        _msg("user", "old question"),
        _msg("assistant", "old answer"),
        _msg("user", "CURRENT REQUEST"),
    ]
    body = _body(messages)
    # count sequence: initial over, after drop1 still over, after drop2 under
    with _mock_count_seq([300000, 250000, 200000]):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    contents = [m.get("content") for m in result["messages"]]
    assert "CURRENT REQUEST" in contents
    assert "old answer" not in contents


def test_system_message_never_dropped() -> None:
    """System prompt is always the first message after compression."""
    groups: list[dict[str, Any]] = []
    for i in range(10):
        groups += [_msg("user", f"q{i}"), _msg("assistant", f"a{i}")]
    messages = [_msg("system", "SYSTEM")] + groups + [_msg("user", "CURRENT")]
    body = _body(messages)
    # Always over budget until only system+last remain
    counts = [300000] * (len(groups) + 2) + [100000]
    with _mock_count_seq(counts):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    assert result["messages"][0]["role"] == "system"
    assert result["messages"][0]["content"] == "SYSTEM"


def test_last_user_message_never_dropped() -> None:
    """The last user message is the final message after all compression."""
    messages = [
        _msg("system", "sys"),
        _msg("user", "old"),
        _msg("assistant", "old resp"),
        _msg("user", "MUST KEEP"),
    ]
    body = _body(messages)
    with _mock_count_seq([300000, 250000, 200000]):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    assert result["messages"][-1]["content"] == "MUST KEEP"


def test_atomic_tool_call_group_dropped_together() -> None:
    """An assistant+tool pair is dropped as one unit, not split."""
    messages = [
        _msg("system", "sys"),
        *_tool_call_group("tc1", "result1"),  # oldest group — should drop
        _msg("user", "CURRENT"),
    ]
    body = _body(messages)
    # count: initial over, after tool-compress still over, after dropping group under
    with _mock_count_seq([300000, 300000, 200000]):
        result = enforce_context_budget(body, {}, FAKE_MODEL)
    roles = [m["role"] for m in result["messages"]]
    # Both assistant and tool from the dropped group should be gone
    assert "tool" not in roles
    # But system and last user must remain
    assert "system" in roles
    assert result["messages"][-1]["content"] == "CURRENT"


# ---------------------------------------------------------------------------
# enforce_context_budget — conversation ends in a tool result, not a plain
# user message (e.g. right after Read/Bash/AskUserQuestion, before the
# client's next natural-language turn) — regression for the Bedrock
# "conversation must start with a user message" bug.
# ---------------------------------------------------------------------------


def test_conversation_ending_in_tool_result_is_never_dropped_to_empty() -> None:
    """When the trailing turn is a tool result (no plain user message to
    protect via the old last-message check), group-dropping must not strip
    every remaining group — every backend rejects a conversation that
    doesn't start with a user turn once system is excluded."""
    route = {
        "backend_max_context_tokens": 10000,
        "reserved_output_tokens": 2000,
        "tokenizer_safety_margin": 1000,
    }  # effective_input_tokens = 7000 -> ~24500 chars at 3.5 chars/token
    messages = [
        _msg("system", "sys"),
        _msg("user", "write me a story " + "x" * 40000),  # forces over budget
        *_tool_call_group("tc1", "genre: Sci-Fi, length: Short"),
    ]
    body = _body(messages)
    with _mock_count(None):  # char-estimate fallback, no mocked call sequence
        result = enforce_context_budget(body, route, FAKE_MODEL)

    non_system_roles = [m["role"] for m in result["messages"] if m["role"] != "system"]
    assert non_system_roles, "must not drop every non-system message"
    assert non_system_roles[0] == "user"


def test_drops_stop_at_last_group_starting_with_user() -> None:
    """Group-dropping may remove an oldest user-starting group, but must
    never cut past the last group that starts with role=="user" — otherwise
    the surviving conversation would start with the trailing assistant+tool
    group instead."""
    route = {
        "backend_max_context_tokens": 10000,
        "reserved_output_tokens": 2000,
        "tokenizer_safety_margin": 1000,
    }  # effective_input_tokens = 7000 -> ~24500 chars at 3.5 chars/token
    messages = [
        _msg("system", "sys"),
        _msg("user", "oldest question " + "x" * 40000),  # droppable; over budget alone
        _msg("user", "recent question"),  # last valid cut point — must survive
        *_tool_call_group("tc1", "recent tool result"),
    ]
    body = _body(messages)
    with _mock_count(None):
        result = enforce_context_budget(body, route, FAKE_MODEL)

    contents = [m.get("content") for m in result["messages"]]
    assert not any(
        isinstance(c, str) and c.startswith("oldest question") for c in contents
    )
    assert "recent question" in contents
    non_system_roles = [m["role"] for m in result["messages"] if m["role"] != "system"]
    assert non_system_roles[0] == "user"


# ---------------------------------------------------------------------------
# enforce_context_budget — stack trace tail preservation (req 9)
# ---------------------------------------------------------------------------


def test_stack_trace_tail_preserved_in_compressed_tool_result() -> None:
    """
    Compiler errors and test failures appear at the end of command output.
    The tail of a compressed tool result must contain the actual error message.
    """
    noisy_prefix = "Running tests...\n" * 400
    error_at_end = "FAILED tests/test_foo.py::test_bar - AssertionError: assert 0 == 42"
    big_trace = noisy_prefix + error_at_end
    compressed = compress_tool_result_text(big_trace)
    assert error_at_end in compressed


# ---------------------------------------------------------------------------
# enforce_context_budget — final request under budget (req 12, last bullet)
# ---------------------------------------------------------------------------


def test_final_translated_request_under_budget_after_compression() -> None:
    """After compression the result token count must satisfy the budget."""
    # effective = 10000 - 1000 - 500 = 8500
    big_tool = "X" * (2 * _TOOL_COMPRESS_THRESHOLD_CHARS)
    messages = [
        _msg("system", "sys"),
        *_tool_call_group("tc1", big_tool),
        _msg("user", "CURRENT"),
    ]
    body = _body(messages)
    route = {
        "backend_max_context_tokens": 10000,
        "reserved_output_tokens": 1000,
        "tokenizer_safety_margin": 500,
    }
    # First count: 9000 (over 8500). After tool compress: 7000 (under 8500).
    with _mock_count_seq([9000, 7000]):
        result = enforce_context_budget(body, route, FAKE_MODEL)
    # Verify the tool result was compressed (proving we went through phase 1)
    tool_msg = next(m for m in result["messages"] if m.get("role") == "tool")
    assert _TRUNCATION_MARKER in tool_msg["content"]


# ---------------------------------------------------------------------------
# enforce_context_budget — truncation marker visible (req 10)
# ---------------------------------------------------------------------------


def test_truncation_marker_visible_in_compressed_result() -> None:
    """Content is never silently removed — the marker makes truncation explicit."""
    big = "line\n" * 5000
    compressed = compress_tool_result_text(big)
    assert "[truncated" in compressed.lower()


# ---------------------------------------------------------------------------
# output budget cap — safe value floor (req 13)
# ---------------------------------------------------------------------------


def test_output_budget_cap_does_not_zero_out_safe_value() -> None:
    """When context is severely exceeded, safe should be floored at 1024 not 0."""
    from language_model_gateway.gateway.routers.model_routing.context_manager import (
        _apply_output_budget_cap,
    )

    # In this scenario, token_count is very high, so:
    # safe = max(1024, backend_max - token_count - 2*safety_margin)
    #      = max(1024, 10000 - 20000 - 1000) = max(1024, -11000) = 1024
    oai_body = {"max_tokens": 5000}
    budget = ContextBudget(
        backend_max_context_tokens=10000,
        reserved_output_tokens=1000,
        tokenizer_safety_margin=500,
    )
    # Simulate severe context overflow
    result = _apply_output_budget_cap(oai_body, 20000, budget)
    assert result["max_tokens"] == 1024
