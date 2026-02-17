import logging
from enum import Enum
from typing import Annotated, Awaitable, Callable, Sequence

from fastapi import APIRouter, Form, params
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class CredentialSubmission(BaseModel):
    """Validated payload produced from the credential capture form."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


CredentialCaptureCallback = Callable[[CredentialSubmission], Awaitable[Response]]


class CredentialCaptureRouter:
    """Router that renders a credential capture form and handles submissions."""

    _form_route: str = "/login"

    def __init__(
        self,
        *,
        prefix: str = "/app",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        callback: CredentialCaptureCallback | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["app"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._callback: CredentialCaptureCallback = callback or self._default_callback
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            self._form_route,
            self.render_form,
            methods=["GET"],
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        self.router.add_api_route(
            self._form_route,
            self.submit_form,
            methods=["POST"],
            include_in_schema=False,
        )

    async def render_form(self) -> HTMLResponse:
        """Serve the username/password capture page."""
        action_path: str = f"{self.prefix}{self._form_route}"
        html = f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Credential Capture</title>
  </head>
  <body style=\"font-family:Arial,Helvetica,sans-serif;background:#f4f6fb;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;\">
    <section style=\"background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);padding:2rem;max-width:420px;width:100%;\">
      <h1 style=\"margin-top:0;color:#1f2a37;font-size:1.5rem;\">Sign in</h1>
      <p style=\"color:#4a5568;font-size:0.95rem;\">Enter your credentials. They are transmitted over the existing HTTPS connection and never stored.</p>
      <form action=\"{action_path}\" method=\"post\">
        <label for=\"username\" style=\"display:block;margin-bottom:0.35rem;color:#1f2937;font-weight:600;\">Username</label>
        <input id=\"username\" name=\"username\" type=\"text\" required style=\"width:100%;padding:0.65rem;border:1px solid #d1d5db;border-radius:6px;margin-bottom:1rem;\" />
        <label for=\"password\" style=\"display:block;margin-bottom:0.35rem;color:#1f2937;font-weight:600;\">Password</label>
        <input id=\"password\" name=\"password\" type=\"password\" required style=\"width:100%;padding:0.65rem;border:1px solid #d1d5db;border-radius:6px;margin-bottom:1.5rem;\" />
        <button type=\"submit\" style=\"width:100%;padding:0.75rem;background:#2563eb;color:#fff;border:none;border-radius:6px;font-size:1rem;cursor:pointer;\">Continue</button>
      </form>
    </section>
  </body>
</html>"""
        return HTMLResponse(content=html)

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
