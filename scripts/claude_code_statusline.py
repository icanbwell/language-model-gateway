#!/usr/bin/env python3
"""Claude Code statusLine command: shows this session's model-routing savings.

Reads Claude Code's statusline JSON payload from stdin (must include
session_id), calls this gateway's
GET /v1/model-routing/sessions/{session_id}/savings, and prints a one-line
summary. Any failure (timeout, network error, 404, malformed response)
prints nothing — a missing footer segment is a normal, silent outcome here,
never a stall or a raw error string in Claude Code's UI.

Configure via ~/.claude/settings.json:
  {"statusLine": {"type": "command", "command": "python3 /path/to/claude_code_statusline.py"}}
and set MODEL_ROUTING_GATEWAY_URL to this gateway's base URL in your shell env.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

_TIMEOUT_SECONDS = 2.0
_TIER_LABELS = {"low": "haiku", "medium": "sonnet", "high": "opus", "fable": "fable"}


def format_savings_line(payload: dict[str, Any]) -> str | None:
    """Format the endpoint's JSON body into a one-line statusline message."""
    total_savings = payload.get("total_savings_usd")
    if total_savings is None:
        return None
    tiers = payload.get("tiers") or {}
    tier_parts = [
        f"{_TIER_LABELS.get(bucket, bucket)} ${tier['cost_usd']:.2f}"
        for bucket, tier in tiers.items()
        if isinstance(tier, dict) and "cost_usd" in tier
    ]
    line = f"\U0001f4b0 ${total_savings:.2f} saved"
    if tier_parts:
        line += " (" + " · ".join(tier_parts) + ")"
    return line


def fetch_savings(gateway_url: str, session_id: str) -> dict[str, Any] | None:
    """GET the session's savings from the gateway. Returns None on any failure."""
    url = f"{gateway_url.rstrip('/')}/v1/model-routing/sessions/{session_id}/savings"
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as resp:  # nosec: B310
            data = json.loads(resp.read())
            if isinstance(data, dict):
                return data
            return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def main() -> None:
    try:
        stdin_payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return
    session_id = stdin_payload.get("session_id")
    if not session_id:
        return
    gateway_url = os.environ.get("MODEL_ROUTING_GATEWAY_URL")
    if not gateway_url:
        return
    savings = fetch_savings(gateway_url, session_id)
    if savings is None:
        return
    line = format_savings_line(savings)
    if line:
        print(line)


if __name__ == "__main__":
    main()
