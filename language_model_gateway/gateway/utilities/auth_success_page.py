from pathlib import Path
from typing import Final

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

_TEMPLATE_NAME: Final[str] = "auth_success.html"
_STATIC_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "static"
_TEMPLATE_PATH: Final[Path] = _STATIC_DIR / _TEMPLATE_NAME

if not _TEMPLATE_PATH.exists():
    raise FileNotFoundError(
        f"Authentication success template not found at {_TEMPLATE_PATH}"
    )

_TEMPLATE_ENV: Final[Environment] = Environment(
    loader=FileSystemLoader(str(_STATIC_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html", "xml")),
)
_AUTH_SUCCESS_TEMPLATE: Final[Template] = _TEMPLATE_ENV.get_template(_TEMPLATE_NAME)


def build_auth_success_page(access_token: str | None) -> HTMLResponse:
    """Render a success page matching the credential capture flow."""
    rendered_content: str = _AUTH_SUCCESS_TEMPLATE.render(access_token=access_token)
    return HTMLResponse(content=rendered_content, media_type="text/html")
