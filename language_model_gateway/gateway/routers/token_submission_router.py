import logging
from enum import Enum
from pathlib import Path
from typing import Annotated, Awaitable, Callable, Sequence

from fastapi import APIRouter, Depends, Form, Query, params
from fastapi.responses import FileResponse, Response
from oidcauthlib.container.inject import Inject

from language_model_gateway.gateway.managers.token_submission_manager import (
    TokenSubmissionManager,
)
from language_model_gateway.gateway.models.token_submission import TokenSubmission
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])

TokenSubmissionCallback = Callable[
    [TokenSubmission, TokenSubmissionManager],
    Awaitable[Response],
]


class TokenSubmissionRouter:
    """Router that renders a token capture form and stores submitted tokens."""

    _form_route: str = "/token"
    _form_template_filename: str = "app_token.html"

    def __init__(
        self,
        *,
        prefix: str = "/app",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        callback: TokenSubmissionCallback | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["app"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags,
            dependencies=self.dependencies,
        )
        self._callback = callback
        self._form_template_path: Path = (
            Path(__file__).resolve().parents[2]
            / "static"
            / self._form_template_filename
        )
        if not self._form_template_path.exists():
            raise FileNotFoundError(
                f"Token capture template not found at {self._form_template_path}"
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
        """Serve the token capture page from the static asset."""
        return FileResponse(path=self._form_template_path, media_type="text/html")

    async def submit_form(
        self,
        token_submission_manager: Annotated[
            TokenSubmissionManager,
            Depends(Inject(TokenSubmissionManager)),
        ],
        token: Annotated[str, Form(min_length=1, max_length=4096)],
        auth_provider: Annotated[str, Query(min_length=1, max_length=255)],
        referring_email: Annotated[str, Query(min_length=3, max_length=320)],
        referring_subject: Annotated[str, Query(min_length=1, max_length=255)],
    ) -> Response:
        submission = TokenSubmission(token=token.strip())
        if self._callback is not None:
            return await self._callback(submission, token_submission_manager)

        return await token_submission_manager.submit_token(
            submission=submission,
            auth_provider=auth_provider,
            referring_email=referring_email,
            referring_subject=referring_subject,
        )

    def get_router(self) -> APIRouter:
        return self.router
