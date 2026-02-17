import logging
from pathlib import Path
from enum import Enum
from typing import Annotated, Awaitable, Callable, Sequence

from fastapi import APIRouter, Form, params
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
import httpx
from fastapi import Depends, HTTPException
from oidcauthlib.container.inject import Inject

from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class CredentialSubmission(BaseModel):
    """Validated payload produced from the credential capture form."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


AppLoginCallback = Callable[
    [
        CredentialSubmission,
        HttpClientFactory,
        LanguageModelGatewayEnvironmentVariables,
    ],
    Awaitable[Response],
]


class AppLoginRouter:
    """Router that renders a credential capture form and handles submissions."""

    _form_route: str = "/login"
    _form_template_filename: str = "app_login.html"

    def __init__(
        self,
        *,
        prefix: str = "/app",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        callback: AppLoginCallback | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["app"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._callback: AppLoginCallback = callback or self._default_callback
        self._form_template_path: Path = (
            Path(__file__).resolve().parents[2]
            / "static"
            / self._form_template_filename
        )
        if not self._form_template_path.exists():
            raise FileNotFoundError(
                f"Credential capture template not found at {self._form_template_path}"
            )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            self._form_route,
            self.render_form,
            methods=["GET"],
            response_class=FileResponse,
            include_in_schema=False,
        )
        self.router.add_api_route(
            self._form_route,
            self.submit_form,
            methods=["POST"],
            include_in_schema=False,
        )

    async def render_form(self) -> FileResponse:
        """Serve the username/password capture page from the static asset."""
        return FileResponse(path=self._form_template_path, media_type="text/html")

    async def submit_form(
        self,
        username: Annotated[str, Form(min_length=1, max_length=255)],
        password: Annotated[str, Form(min_length=1, max_length=255)],
        http_client_factory: Annotated[
            HttpClientFactory, Depends(Inject(HttpClientFactory))
        ],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> Response:
        submission = CredentialSubmission(username=username.strip(), password=password)
        return await self._callback(
            submission,
            http_client_factory,
            environment_variables,
        )

    async def _default_callback(
        self,
        submission: CredentialSubmission,
        http_client_factory: HttpClientFactory,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
    ) -> Response:
        base_url = environment_variables.app_login_base_url
        client_key = environment_variables.app_login_client_key
        origin = environment_variables.app_login_origin
        referer = environment_variables.app_login_referer

        if base_url is None:
            raise HTTPException(status_code=500, detail="APP_LOGIN_BASE_URL not set")
        if client_key is None:
            raise HTTPException(status_code=500, detail="APP_LOGIN_CLIENT_KEY not set")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "clientkey": client_key,
        }
        if origin is not None:
            headers["origin"] = origin
        if referer is not None:
            headers["referer"] = referer

        try:
            async with http_client_factory.create_http_client(
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

    def get_router(self) -> APIRouter:
        return self.router
