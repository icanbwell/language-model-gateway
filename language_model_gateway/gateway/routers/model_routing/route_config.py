from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_CONFIG_PATH = Path(
    os.environ.get("ROUTER_CONFIG", Path.home() / "model-router" / "router_config.json")
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


_CONFIG: dict[str, Any] = _load_config()
_ROUTES: dict[str, dict[str, Any]] = {}
for _r in _CONFIG.get("routes", []):
    _key = _r["claude_model"]
    if _key in _ROUTES:
        logger.warning(
            "[coding-model-router] duplicate route for model '%s' — later entry wins",
            _key,
        )
    _ROUTES[_key] = _r


def _find_route(model: str) -> dict[str, Any] | None:
    return _ROUTES.get(model)
