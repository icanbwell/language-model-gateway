import logging
from pathlib import Path
from enum import Enum
from typing import Annotated, Awaitable, Callable, Sequence

from fastapi import APIRouter, Form, params
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class CredentialSubmission(BaseModel):
    """Validated payload produced from the credential capture form."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


AppLoginCallback = Callable[[CredentialSubmission], Awaitable[Response]]


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
    ) -> Response:
        submission = CredentialSubmission(username=username.strip(), password=password)
        return await self._callback(submission)

    async def _default_callback(self, submission: CredentialSubmission) -> Response:
        return JSONResponse(
            {
                "message": f"Credentials received. {submission.username=} {submission.password=}"
            }
        )

    def get_router(self) -> APIRouter:
        return self.router
