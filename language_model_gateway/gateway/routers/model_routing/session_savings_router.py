"""Read-only endpoint for a Claude Code session's model-routing savings.

Deliberately unauthenticated (session_id-as-capability) — see
docs/superpowers/specs/2026-07-16-session-savings-statusline-design.md
("Security posture") for the reasoning. Returns only an aggregate cost
figure — no prompt/response content, no PHI, no email/account identity.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Sequence

from fastapi import APIRouter, HTTPException, params

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavings,
    SessionSavingsReader,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_NOT_FOUND_DETAIL = "no usage recorded for this session"


class SessionSavingsRouter:
    """Exposes GET {prefix}/sessions/{session_id}/savings."""

    def __init__(
        self,
        *,
        prefix: str = "/v1/model-routing",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        mongo_uri: str | None = None,
        db_name: str = "llm_storage",
        collection_name: str = "model-router-sessions",
    ) -> None:
        self.router = APIRouter(
            prefix=prefix,
            tags=tags or ["model-routing-savings"],
            dependencies=dependencies or [],
        )
        self._reader: SessionSavingsReader | None = None
        if mongo_uri:
            self._reader = SessionSavingsReader(
                mongo_uri=mongo_uri,
                db_name=db_name,
                collection_name=collection_name,
                enabled=True,
            )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/sessions/{session_id}/savings",
            self.get_session_savings,
            methods=["GET"],
            response_model=SessionSavings,
            summary="Get model-routing savings for a Claude Code session",
            description=(
                "Returns this gateway's cumulative cost savings (vs. "
                "Anthropic list price) for the given Claude Code session_id, "
                "broken down by model tier."
            ),
            status_code=200,
        )

    async def get_session_savings(self, session_id: str) -> SessionSavings:
        if self._reader is None:
            raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
        savings = await self._reader.get_session_savings(session_id)
        if savings is None:
            raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
        return savings

    def get_router(self) -> APIRouter:
        return self.router
