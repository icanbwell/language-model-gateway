"""
Verifies the session-savings route is mounted by create_app().

Route matching (rather than inspecting `app.routes` for `APIRoute`
instances directly) is used because FastAPI 0.139's `include_router()`
wraps included routers in an internal `_IncludedRouter` object, so a
mounted route's `APIRoute` is not a direct top-level member of
`app.routes` -- but `Route.matches()` is the same dispatch mechanism
FastAPI/Starlette use internally, so it reflects reality regardless of
how routers are wrapped.
"""

from __future__ import annotations

from starlette.routing import Match

from language_model_gateway.gateway.api import create_app


def test_session_savings_route_is_mounted() -> None:
    app = create_app()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/model-routing/sessions/abc123/savings",
        "headers": [],
    }
    assert any(route.matches(scope)[0] == Match.FULL for route in app.routes)
