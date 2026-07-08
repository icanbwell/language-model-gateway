from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_CONFIG_PATH = Path(
    os.environ.get(
        "ROUTER_CONFIG",
        Path(__file__).parent / "model-router-config.json",
    )
)


def _load_config() -> dict[str, Any]:
    try:
        with open(_CONFIG_PATH) as f:
            result: dict[str, Any] = json.load(f)
            return result
    except FileNotFoundError:
        logger.warning(
            "[coding-model-router] config not found at %s — no routes configured; "
            "unknown models fall back to Anthropic direct",
            _CONFIG_PATH,
        )
        return {"routes": []}


def _build_routes(
    config: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[tuple[re.Pattern[str], dict[str, Any]]]]:
    """
    Build the exact-match route dict and the ordered pattern fallback list.

    Each route's `claude_model` is the exact (and fastest) lookup key. An
    optional `claude_model_pattern` regex lets a single route also match
    version bumps (e.g. claude-sonnet-4-6 → claude-sonnet-5) without needing
    a new config entry every time Claude Code's default model id changes.
    """
    routes: dict[str, dict[str, Any]] = {}
    patterns: list[tuple[re.Pattern[str], dict[str, Any]]] = []
    for route in config.get("routes", []):
        key = route["claude_model"]
        if key in routes:
            logger.warning(
                "[coding-model-router] duplicate route for model '%s' — later entry wins",
                key,
            )
        routes[key] = route
        if pattern := route.get("claude_model_pattern"):
            patterns.append((re.compile(pattern), route))
    return routes, patterns


# Note: Config loaded at module import time and cached globally.
# In production, containers are restarted when config changes via volume mounts.
# For runtime config reload, call _reload_routes() to refresh _ROUTES from disk.
_CONFIG: dict[str, Any] = _load_config()
_ROUTES: dict[str, dict[str, Any]]
_PATTERNS: list[tuple[re.Pattern[str], dict[str, Any]]]
_ROUTES, _PATTERNS = _build_routes(_CONFIG)


def _find_route(model: str) -> dict[str, Any] | None:
    """Exact match first (fast path), then the first matching tier pattern."""
    if route := _ROUTES.get(model):
        return route
    for pattern, route in _PATTERNS:
        if pattern.search(model):
            return route
    return None


def _reload_routes() -> dict[str, dict[str, Any]]:
    """Reload routes from disk and return the updated exact-match routes dict."""
    global _CONFIG, _ROUTES, _PATTERNS
    _CONFIG = _load_config()
    _ROUTES, _PATTERNS = _build_routes(_CONFIG)
    return _ROUTES
