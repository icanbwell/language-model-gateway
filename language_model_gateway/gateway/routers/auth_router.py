import logging
import os
import traceback

from enum import Enum
from typing import Any, Sequence, Annotated, Union

from fastapi import APIRouter
from fastapi import params
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import JSONResponse

from language_model_gateway.gateway.api_container import get_auth_manager
from language_model_gateway.gateway.auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)


class AuthRouter:
    def __init__(
        self,
        *,
        prefix: str = "/auth",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
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
            "/callback", self.auth_callback, methods=["GET", "POST"]
        )

    # noinspection PyMethodMayBeStatic
    async def login(
        self,
        request: Request,
        auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
        audience: str | None = None,
    ) -> Union[RedirectResponse, JSONResponse]:
        redirect_uri1: URL = request.url_for("auth_callback")

        try:
            if audience is None:
                audience = os.getenv("AUTH_CLIENT_ID_bwell-client-id")
            assert audience is not None
            issuer = os.getenv(f"AUTH_ISSUER-{audience}")
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
    ) -> JSONResponse:
        logger.info(f"Received request for auth callback: {request.url}")
        # return JSONResponse(
        #     content={"message": "Processing auth callback..."},
        #     status_code=200,
        # )
        try:
            content: dict[str, Any] = await auth_manager.read_callback_response(
                request=request,
            )
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
