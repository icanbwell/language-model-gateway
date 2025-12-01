import logging
from typing import Optional

from starlette.responses import Response, StreamingResponse

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["FILES"])


class FileManager:
    # noinspection PyMethodMayBeStatic
    async def save_file_async(
        self,
        *,
        file_data: bytes,
        folder: str,
        filename: str,
        content_type: str,
    ) -> Optional[str]:
        raise NotImplementedError("Must be implemented in a subclass")

    # noinspection PyMethodMayBeStatic
    def get_full_path(self, *, filename: str, folder: str) -> str:
        raise NotImplementedError("Must be implemented in a subclass")

    async def read_file_async(
        self, *, folder: str, file_path: str
    ) -> StreamingResponse | Response:
        raise NotImplementedError("Must be implemented in a subclass")

    @staticmethod
    async def extract_content(response: StreamingResponse) -> str:
        """
        Extracts and returns content from a streaming response.
        :param response: (StreamingResponse) s3 response for the file
        :return: returns the file content in string format.
        """
        extracted_content = ""
        async for chunk in response.body_iterator:
            if not isinstance(chunk, bytes):
                raise TypeError(f"Expected bytes, got {type(chunk)}")
            extracted_content += chunk.decode("utf-8")

        return extracted_content
