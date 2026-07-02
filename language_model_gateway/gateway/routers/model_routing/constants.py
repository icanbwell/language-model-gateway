from __future__ import annotations

import re

_OAI_TO_ANT_STOP = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}

_ANTHROPIC_ONLY_HEADERS = frozenset(
    {"anthropic-version", "anthropic-beta", "x-api-key"}
)

_SKIP_HEADERS = frozenset(
    {"host", "content-length", "transfer-encoding", "authorization"}
)

_HOP_BY_HOP_HEADERS = frozenset(
    {"content-encoding", "transfer-encoding", "connection", "keep-alive"}
)

_BEDROCK_MIN_DISPATCH_INTERVAL_S = 0.3
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

# Safety margin subtracted from the computed remaining-token cap to absorb estimation
# imprecision (4 chars ≈ 1 token is a heuristic; dense content like JSON and tool
# schemas can tokenize at higher density, causing the estimate to fall short by a few
# tokens even after the 1.20x multiplier).
_TOKEN_ESTIMATE_SAFETY_BUFFER = 100
