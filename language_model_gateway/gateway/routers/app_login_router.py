import logging
from pathlib import Path
from enum import Enum
from typing import Annotated, Awaitable, Callable, Mapping, Sequence

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, params
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from oidcauthlib.container.inject import Inject

from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.managers.app_login_manager import AppLoginManager
from language_model_gateway.gateway.models.app_login_submission import (
    CredentialSubmission,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


AppLoginCallback = Callable[
    [
        CredentialSubmission,
        HttpClientFactory,
        LanguageModelGatewayEnvironmentVariables,
        str | None,
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
        clients: Mapping[str, str] | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["app"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._callback: AppLoginCallback | None = callback
        self._clients: dict[str, str] = dict(clients or {})
        self._form_template_path: Path = (
            Path(__file__).resolve().parents[2]
            / "static"
            / self._form_template_filename
        )
        if not self._form_template_path.exists():
            raise FileNotFoundError(
                f"Credential capture template not found at {self._form_template_path}"
            )
        self._templates = Jinja2Templates(
            directory=str(self._form_template_path.parent)
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            self._form_route,
            self.render_form,
            methods=["GET"],
            include_in_schema=False,
        )
        self.router.add_api_route(
            self._form_route,
            self.submit_form,
            methods=["POST"],
            include_in_schema=False,
        )

    async def render_form(self, request: Request) -> Response:
        """Serve the username/password capture page from the static asset."""
        return self._templates.TemplateResponse(
            name=self._form_template_filename,
            context={
                "request": request,
                "clients": self._clients,
            },
            media_type="text/html",
        )

    async def submit_form(
        self,
        app_login_manager: Annotated[
            AppLoginManager,
            Depends(Inject(AppLoginManager)),
        ],
        http_client_factory: Annotated[
            HttpClientFactory, Depends(Inject(HttpClientFactory))
        ],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
        username: Annotated[str, Form(min_length=1, max_length=255)],
        password: Annotated[str, Form(min_length=1, max_length=255)],
        auth_provider: Annotated[str, Query(min_length=1, max_length=255)],
        referring_email: Annotated[str, Query(min_length=3, max_length=320)],
        referring_subject: Annotated[str, Query(min_length=1, max_length=255)],
        client_key: Annotated[str | None, Form(min_length=1, max_length=255)] = None,
    ) -> Response:
        submission = CredentialSubmission(username=username.strip(), password=password)
        resolved_client_key = self._resolve_auth_client_key(
            provided_client_key=client_key,
            environment_variables=environment_variables,
        )
        if self._callback is not None:
            return await self._callback(
                submission,
                http_client_factory,
                environment_variables,
                resolved_client_key,
            )

        return await app_login_manager.login(
            submission=submission,
            auth_provider=auth_provider,
            auth_client_key=resolved_client_key,
            referring_email=referring_email,
            referring_subject=referring_subject,
        )

    def get_router(self) -> APIRouter:
        return self.router

    def _resolve_auth_client_key(
        self,
        *,
        provided_client_key: str | None,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
    ) -> str:
        if self._clients:
            if not provided_client_key:
                raise HTTPException(
                    status_code=400,
                    detail="client_key is required",
                )
            if provided_client_key not in self._clients.values():
                raise HTTPException(
                    status_code=400,
                    detail="client_key is invalid",
                )
            return provided_client_key

        if provided_client_key:
            return provided_client_key

        env_client_key = environment_variables.app_login_client_key
        if env_client_key:
            return env_client_key

        raise HTTPException(
            status_code=500,
            detail="APP_LOGIN_CLIENT_KEY not configured",
        )
