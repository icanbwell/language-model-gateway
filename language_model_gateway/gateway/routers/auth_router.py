import logging
import traceback

from enum import Enum
from typing import Any, Sequence, Annotated, Union, List

from fastapi import APIRouter
from fastapi import params
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

from language_model_gateway.gateway.api_container import (
    get_auth_manager,
    get_auth_config_reader,
)
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.config.auth_config import AuthConfig
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)

logger = logging.getLogger(__name__)


class AuthRouter:
    """
    AuthRouter is a FastAPI router for handling authentication-related routes.
    """

    def __init__(
        self,
        *,
        prefix: str = "/auth",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        """
        Initialize the AuthRouter with a prefix, tags, and dependencies.
        Args:
            prefix (str): The prefix for the router's routes, default is "/auth".
            tags (list[str | Enum] | None): Tags to categorize the routes, default is ["models"].
            dependencies (Sequence[params.Depends] | None): Dependencies to be applied to all routes in this router, default is an empty list.
        """
        self.prefix = prefix
        self.tags = tags or ["models"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes for this router"""
        self.router.add_api_route(
            "/login", self.login, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/callback",
            self.auth_callback,
            methods=["GET", "POST"],
            response_model=None,
        )

    # noinspection PyMethodMayBeStatic
    async def login(
        self,
        request: Request,
        auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
        auth_config_reader: Annotated[
            AuthConfigReader, Depends(get_auth_config_reader)
        ],
        audience: str | None = None,
    ) -> Union[RedirectResponse, JSONResponse]:
        """
        Handle the login route for authentication.
        This route initiates the authentication process by redirecting the user to the
        authorization server's login page.
        Args:
            request (Request): The incoming request object.
            auth_manager (AuthManager): The authentication manager instance.
            auth_config_reader (AuthConfigReader): The authentication configuration reader instance.
            audience (str | None): The audience for which to authenticate. If None, the first audience from the config will be used.
        """
        redirect_uri1: URL = request.url_for("auth_callback")

        try:
            if audience is None:
                auth_configs: List[AuthConfig] = (
                    auth_config_reader.get_auth_configs_for_all_audiences()
                )
                audience = auth_configs[0].audience if auth_configs else None
            assert audience is not None
            auth_config: AuthConfig | None = auth_config_reader.get_config_for_audience(
                audience=audience
            )
            assert auth_config is not None
            issuer: str | None = auth_config.issuer
            assert issuer is not None, (
                f"AUTH_ISSUER-{audience} environment variable must be set"
            )
            url = await auth_manager.create_authorization_url(
                redirect_uri=str(redirect_uri1),
                audience=audience,
                issuer=issuer,
                url=str(request.url),
            )

            return RedirectResponse(url, status_code=302)
        except Exception as e:
            exc: str = traceback.format_exc()
            logger.error(f"Error processing auth login: {e}\n{exc}")
            return JSONResponse(
                content={"error": f"Error processing auth login: {e}\n{exc}"},
                status_code=500,
            )

    # noinspection PyMethodMayBeStatic
    async def auth_callback(
        self,
        request: Request,
        auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
    ) -> Union[JSONResponse, HTMLResponse]:
        logger.info(f"Received request for auth callback: {request.url}")
        try:
            content: dict[str, Any] = await auth_manager.read_callback_response(
                request=request,
            )
            if not logger.isEnabledFor(logging.DEBUG):
                from starlette.responses import HTMLResponse

                html_content = """
                <html>
                    <head><title>Token Saved</title></head>
                    <body>
                        <h2>Your new token has been saved.</h2>
                        <p>You can now retry your question.</p>
                    </body>
                </html>
                """
                return HTMLResponse(content=html_content, status_code=200)
            return JSONResponse(content)
        except Exception as e:
            exc: str = traceback.format_exc()
            logger.error(f"Error processing auth callback: {e}\n{exc}")
            return JSONResponse(
                content={"error": f"Error processing auth callback: {e}\n{exc}"},
                status_code=500,
            )

    def get_router(self) -> APIRouter:
        """ """
        return self.router
