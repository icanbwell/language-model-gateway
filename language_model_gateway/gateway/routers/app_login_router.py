import logging
from pathlib import Path
from enum import Enum
from typing import Annotated, Sequence

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
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["app"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
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

    async def render_form(
        self,
        request: Request,
        app_login_manager: Annotated[
            AppLoginManager,
            Depends(Inject(AppLoginManager)),
        ],
    ) -> Response:
        """Serve the username/password capture page from the static asset."""
        auth_provider: str | None = request.query_params.get("auth_provider")
        if not auth_provider:
            raise HTTPException(
                status_code=400,
                detail="auth_provider query parameter is required to render login form",
            )
        # get client keys from the specified auth provider if clients are configured
        client_keys: (
            dict[str, str] | None
        ) = await app_login_manager.get_client_keys_for_auth_provider(
            auth_provider=auth_provider
        )
        return self._templates.TemplateResponse(
            name=self._form_template_filename,
            context={
                "request": request,
                "clients": client_keys,
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
        """
        Handle form submission, invoking the callback if provided or the manager method otherwise.
        """
        if auth_provider is None:
            raise HTTPException(
                status_code=400,
                detail="auth_provider query parameter is required",
            )
        if username is None:
            raise HTTPException(
                status_code=400,
                detail="username form field is required",
            )
        if password is None:
            raise HTTPException(
                status_code=400,
                detail="password form field is required",
            )
        if client_key is None:
            raise HTTPException(
                status_code=400,
                detail="client_key form field is required",
            )
        submission = CredentialSubmission(username=username.strip(), password=password)

        return await app_login_manager.login(
            submission=submission,
            auth_provider=auth_provider,
            auth_client_key=client_key,
            referring_email=referring_email,
            referring_subject=referring_subject,
        )

    def get_router(self) -> APIRouter:
        return self.router
