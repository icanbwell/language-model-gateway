import json
import logging
from typing import Any

import httpx
from fastapi.responses import JSONResponse
from httpx_sse import aconnect_sse
from starlette.responses import Response

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class SkillPublishClient:
    """Proxies skill publish requests to the mcp-server-gateway REST API.

    The upstream endpoint returns an SSE stream with keepalive, complete, and
    error events.  This client consumes the stream and returns a single JSON
    response once the terminal event arrives.
    """

    def __init__(self, *, mcp_server_gateway_url: str) -> None:
        self._mcp_server_gateway_url = mcp_server_gateway_url

    async def publish(self, *, body: dict[str, Any], auth_header: str) -> Response:
        rest_url = f"{self._mcp_server_gateway_url}/api/skills/publish"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                return await self._consume_sse(client, rest_url, headers, body)
            except httpx.HTTPError as exc:
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Network error: {exc}"},
                )

    async def _consume_sse(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> Response:
        async with aconnect_sse(
            client, "POST", url, json=body, headers=headers
        ) as event_source:
            if event_source.response.status_code != 200:
                raw = await event_source.response.aread()
                try:
                    content = json.loads(raw)
                except Exception:
                    content = {
                        "error": raw.decode(errors="replace")
                        or f"HTTP {event_source.response.status_code}"
                    }
                return JSONResponse(
                    status_code=event_source.response.status_code,
                    content=content,
                )

            async for sse in event_source.aiter_sse():
                if sse.event == "keepalive":
                    continue
                if sse.event == "complete":
                    try:
                        data = json.loads(sse.data)
                    except Exception:
                        data = {"message": sse.data}
                    return JSONResponse(status_code=200, content=data)
                if sse.event == "error":
                    try:
                        data = json.loads(sse.data)
                    except Exception:
                        data = {"error": sse.data}
                    return JSONResponse(status_code=500, content=data)

        return JSONResponse(
            status_code=502,
            content={"error": "SSE stream ended without a terminal event"},
        )
