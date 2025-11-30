import logging
from enum import Enum
from typing import Annotated, List, Sequence

from fastapi import APIRouter, Depends
from fastapi import params
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from language_model_gateway.gateway.file_managers.file_manager import FileManager
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.url_parser import UrlParser
from oidcauthlib.container.inject import Inject

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["IMAGE_GENERATION"])


class ImagesRouter:
    """
    Router class for models endpoints
    """

    def __init__(
        self,
        *,
        prefix: str = "",
        image_generation_path: str,
        allowed_extensions: List[str] | None = None,
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["models"]
        self.allowed_extensions = allowed_extensions
        self.image_generation_path = image_generation_path
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes for this router"""
        self.router.add_api_route(
            "/image_generation/{file_path:path}",  # Add path parameter to capture the full path
            self.get_images,
            methods=["GET"],
            response_model=None,
            summary="Download images",
            description="Download images",
            response_description="Images",
            status_code=200,
        )

    def check_extension(self, filename: str) -> bool:
        if not self.allowed_extensions:
            return True
        return any(
            filename.lower().endswith(ext.lower()) for ext in self.allowed_extensions
        )

    # noinspection PyMethodMayBeStatic
    async def get_images(
        self,
        request: Request,
        file_path: str,  # Add this parameter to capture the file path
        file_manager_factory: Annotated[
            FileManagerFactory, Depends(Inject(FileManagerFactory))
        ],
    ) -> Response | StreamingResponse:
        """
        Get models endpoint. model_manager is injected by FastAPI.

        Args:
            request: The incoming request
            file_manager_factory: Injected model manager instance
            file_path: The file path to download

        Returns:
            Dictionary containing list of available models
        """
        request_url_path = file_path
        logger.info(f"get_images: file_path: {file_path}")
        folder: str
        file_path1: str
        if self.image_generation_path.startswith("s3"):
            bucket_name, prefix = UrlParser.parse_s3_uri(self.image_generation_path)
            # Check file extension
            file_path1 = str(request_url_path)
            # remove the target path
            file_path1 = file_path1[len(self.prefix) :]

            if not self.check_extension(file_path1):
                return Response(status_code=403, content="File type not allowed")

            # combine the prefix and file path and include / if needed
            s3_key = UrlParser.combine_path(prefix=prefix, filename=file_path)
            folder = bucket_name
            file_path1 = s3_key
        else:
            # read and return file
            request_url_path = request_url_path[len(self.prefix) :]
            folder = self.image_generation_path
            file_path1 = request_url_path

        # now stream the file
        file_manager: FileManager = file_manager_factory.get_file_manager(
            folder=self.image_generation_path
        )
        return await file_manager.read_file_async(
            folder=folder,
            file_path=file_path1,
        )

    def get_router(self) -> APIRouter:
        """Get the configured router"""
        return self.router
