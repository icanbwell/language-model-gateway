import logging
import mimetypes
import os
from os import makedirs
from pathlib import Path
from typing import Optional, AsyncGenerator, override

from fastapi import HTTPException
from starlette.responses import StreamingResponse

from language_model_gateway.gateway.file_managers.file_manager import FileManager
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["FILES"])


class LocalFileManager(FileManager):
    @override
    async def save_file_async(
        self,
        *,
        file_data: bytes,
        folder: str,
        filename: str,
        content_type: str = "image/png",
    ) -> Optional[str]:
        """Save the generated image to a file"""
        file_path: str = self.get_full_path(filename=filename, folder=folder)
        if file_data:
            with open(file_path, "wb") as f:
                f.write(file_data)
            logger.info(f"Image saved as {file_path}")
            return str(file_path)
        else:
            logger.error("No image to save")
            return None

    @override
    def get_full_path(self, *, filename: str, folder: str) -> str:
        image_generation_path = Path(folder)
        makedirs(image_generation_path, exist_ok=True)
        file_path: Path = image_generation_path / filename
        return str(file_path)

    # @override
    # async def save_image_async(self, image_data: bytes, filename: Path) -> None:
    #     """Save the generated image to a file asynchronously"""
    #     if not image_data:
    #         logger.warning("No image data to save")
    #         return
    #
    #     try:
    #         # Use aiofiles for async file operations
    #         async with aiofiles.open(filename, mode='wb') as f:
    #             await f.write(image_data)
    #         logger.info(f"Image saved as {filename}")
    #
    #     except Exception as e:
    #         logger.error(f"Error saving image to {filename}: {str(e)}")
    #         raise

    @override
    async def read_file_async(
        self, *, folder: str, file_path: str
    ) -> StreamingResponse:
        full_path: str = str(Path(folder) / Path(file_path))
        try:
            # Determine file size and MIME type
            file_size = os.path.getsize(full_path)
            mime_type, _ = mimetypes.guess_type(full_path)
            mime_type = mime_type or "application/octet-stream"

            # Open file as a generator to stream content
            async def file_iterator() -> AsyncGenerator[bytes, None]:
                with open(full_path, "rb") as file:
                    while chunk := file.read(4096):  # Read in 4KB chunks
                        yield chunk

            return StreamingResponse(
                file_iterator(),
                media_type=mime_type,
                headers={
                    "Content-Length": str(file_size),
                    "Content-Disposition": f'inline; filename="{os.path.basename(full_path)}"',
                },
            )
        except FileNotFoundError:
            logger.error(f"File not found: {full_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
        except PermissionError:
            logger.error(f"Access forbidden: {full_path}")
            raise HTTPException(
                status_code=403, detail=f"Access forbidden: {full_path}"
            )
