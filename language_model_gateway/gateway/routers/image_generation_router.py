import logging
from enum import Enum
from typing import Annotated, Dict, Sequence, Any, cast

from botocore.exceptions import TokenRetrievalError
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from fastapi import params
from starlette.responses import JSONResponse, StreamingResponse

from language_model_gateway.gateway.api_container import get_image_generation_manager
from language_model_gateway.gateway.managers.image_generation_manager import (
    ImageGenerationManager,
)
from language_model_gateway.gateway.schema.openai.image_generation import (
    ImageGenerationRequest,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["IMAGE_GENERATION"])


class ImageGenerationRouter:
    """
    Router class for image generation endpoints
    """

    def __init__(
        self,
        *,
        prefix: str = "/api/v1",
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
            "/images/generations",
            self.generate_image,
            methods=["POST"],
            response_model=None,
            summary="Complete a chat prompt",
            description="Completes a chat prompt using the specified model",
            response_description="Chat completions",
            status_code=200,
        )

    # noinspection PyMethodMayBeStatic
    async def generate_image(
        self,
        request: Request,
        image_generation_request: Dict[str, Any],
        model_manager: Annotated[
            ImageGenerationManager, Depends(get_image_generation_manager)
        ],
    ) -> StreamingResponse | JSONResponse:
        """
        Get models endpoint. model_manager is injected by FastAPI.

        Args:
            request: The incoming request
            image_generation_request: The image generation request
            model_manager: Injected model manager instance

        Returns:
            Dictionary containing list of available models
        """
        try:
            return await model_manager.generate_image_async(
                image_generation_request=cast(
                    ImageGenerationRequest, image_generation_request
                ),
                headers={k: v for k, v in request.headers.items()},
            )
        except TokenRetrievalError as e:
            logger.exception(e, stack_info=True)
            # return JSONResponse(content=f"Error retrieving AWS token: {e}", status_code=500)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving AWS token: {e}.  If running on developer machines, run `aws sso login --profile [profile_name]` to get the token.",
            )
        except Exception as e:
            logger.exception("Error generating image", e)
            # return JSONResponse(content=f"Error generating image: {e}", status_code=500)
            raise HTTPException(
                status_code=500, detail=f"Error retrieving AWS token: {e}"
            )

    def get_router(self) -> APIRouter:
        """Get the configured router"""
        return self.router
