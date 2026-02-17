import logging
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.models.app_login_submission import (
    CredentialSubmission,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class AppLoginManager:
    """Handle credential submissions for app logins."""

    def __init__(
        self,
        *,
        http_client_factory: HttpClientFactory,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
    ) -> None:
        if http_client_factory is None:
            raise ValueError("http_client_factory must not be None")
        if environment_variables is None:
            raise ValueError("environment_variables must not be None")

        self._http_client_factory = http_client_factory
        self._environment_variables = environment_variables

    async def login(self, submission: CredentialSubmission) -> JSONResponse:
        base_url = self._environment_variables.app_login_base_url
        client_key = self._environment_variables.app_login_client_key
        origin = self._environment_variables.app_login_origin
        referer = self._environment_variables.app_login_referer

        if not base_url:
            raise HTTPException(status_code=500, detail="APP_LOGIN_BASE_URL not set")
        if client_key is None:
            raise HTTPException(status_code=500, detail="APP_LOGIN_CLIENT_KEY not set")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "clientkey": client_key,
        }
        if origin:
            headers["origin"] = origin
        if referer:
            headers["referer"] = referer

        try:
            async with self._http_client_factory.create_http_client(
                base_url=base_url,
                headers=headers,
            ) as client:
                response = await client.post(
                    "/identity/account/login",
                    json={
                        "email": submission.username,
                        "password": submission.password,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "App login failed with HTTP status %s", exc.response.status_code
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail="Login request failed",
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("App login request could not be completed")
            raise HTTPException(
                status_code=502, detail="Unable to reach login service"
            ) from exc

        payload: dict[str, Any]
        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception("Login service returned invalid JSON")
            raise HTTPException(
                status_code=502, detail="Invalid response from login service"
            ) from exc

        access_token = payload.get("accessToken", {}).get("jwtToken")
        if not access_token:
            logger.warning("Login service response did not include access token")
            raise HTTPException(
                status_code=502, detail="Access token missing in login response"
            )

        return JSONResponse({"accessToken": access_token})
