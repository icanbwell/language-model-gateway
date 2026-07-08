"""
Tests for route_config.py — exact and pattern-based model routing.

Covers the bug where a stale exact `claude_model` key (e.g. after a Claude
model version bump) silently falls back to Anthropic direct, bypassing
cost-routing and context-budget enforcement.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from language_model_gateway.gateway.routers.model_routing.route_config import (
    _build_routes,
    _find_route,
)

# ---------------------------------------------------------------------------
# _build_routes
# ---------------------------------------------------------------------------


def test_build_routes_exact_key() -> None:
    config = {"routes": [{"claude_model": "claude-opus-4-8", "model": "upstream-opus"}]}
    routes, patterns = _build_routes(config)
    assert routes["claude-opus-4-8"]["model"] == "upstream-opus"
    assert patterns == []


def test_build_routes_compiles_pattern() -> None:
    config = {
        "routes": [
            {
                "claude_model": "claude-sonnet-5",
                "claude_model_pattern": "^claude-sonnet(-|$)",
                "model": "upstream-sonnet",
            }
        ]
    }
    _routes, patterns = _build_routes(config)
    assert len(patterns) == 1
    compiled, route = patterns[0]
    assert route["model"] == "upstream-sonnet"
    assert compiled.search("claude-sonnet-6")
    assert not compiled.search("claude-opus-4-8")


# ---------------------------------------------------------------------------
# _find_route
# ---------------------------------------------------------------------------


def test_find_route_prefers_exact_match_over_pattern() -> None:
    fake_routes = {"claude-a": {"model": "exact"}}
    fake_patterns = [(re.compile("^claude-a"), {"model": "pattern"})]
    with (
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._ROUTES",
            fake_routes,
        ),
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._PATTERNS",
            fake_patterns,
        ),
    ):
        route = _find_route("claude-a")
    assert route is not None
    assert route["model"] == "exact"


def test_find_route_falls_back_to_pattern_when_no_exact_match() -> None:
    fake_patterns = [(re.compile(r"^claude-sonnet(-|$)"), {"model": "sonnet-backend"})]
    with (
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._ROUTES",
            {},
        ),
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._PATTERNS",
            fake_patterns,
        ),
    ):
        route = _find_route("claude-sonnet-6")
    assert route is not None
    assert route["model"] == "sonnet-backend"


def test_find_route_no_match_returns_none() -> None:
    with (
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._ROUTES",
            {},
        ),
        patch(
            "language_model_gateway.gateway.routers.model_routing.route_config._PATTERNS",
            [],
        ),
    ):
        assert _find_route("totally-unknown-model") is None


# ---------------------------------------------------------------------------
# Regression: live model-router-config.json must resolve current model ids
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model,expected_tier",
    [
        ("claude-haiku-4-5-20251001", "haiku"),
        ("claude-sonnet-5", "sonnet"),
        ("claude-opus-4-8", "opus"),
        ("claude-fable-5", "fable"),
    ],
)
def test_live_config_resolves_current_model_ids(model: str, expected_tier: str) -> None:
    route = _find_route(model)
    assert route is not None, (
        f"model '{model}' has no route in model-router-config.json"
    )
    assert route["tier"] == expected_tier


def test_live_config_sonnet_pattern_survives_version_bump() -> None:
    """The sonnet tier must match future version bumps via pattern, not just
    the pinned exact id — this is the recurrence-prevention case for the bug
    where claude-sonnet-4-6 stayed configured after Claude Code moved to
    claude-sonnet-5."""
    route = _find_route("claude-sonnet-7")
    assert route is not None
    assert route["tier"] == "sonnet"


def test_live_config_still_supports_old_sonnet_model() -> None:
    """Bumping the primary sonnet id to claude-sonnet-5 must not drop support
    for clients still pinned to the previous claude-sonnet-4-6 id — both
    should resolve to the same sonnet-tier route."""
    old_route = _find_route("claude-sonnet-4-6")
    new_route = _find_route("claude-sonnet-5")
    assert old_route is not None
    assert new_route is not None
    assert old_route["tier"] == "sonnet"
    assert old_route["model"] == new_route["model"]
