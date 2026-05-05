import logging
from typing import Any

import httpx
from fastapi.responses import JSONResponse
from starlette.responses import Response

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class SkillPublishClient:
    """Proxies skill publish requests to the mcp-server-gateway REST API."""

    def __init__(self, *, mcp_server_gateway_url: str) -> None:
        self._mcp_server_gateway_url = mcp_server_gateway_url

    async def publish(self, *, body: dict[str, Any], auth_header: str) -> Response:
        rest_url = f"{self._mcp_server_gateway_url}/api/skills/publish"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(rest_url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Network error: {exc}"},
                )

        try:
            content = response.json()
        except Exception:
            content = {"error": response.text or f"HTTP {response.status_code}"}

        return JSONResponse(
            status_code=response.status_code,
            content=content,
        )
