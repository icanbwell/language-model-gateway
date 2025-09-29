from typing import Dict

from starlette.responses import JSONResponse, StreamingResponse

from language_model_gateway.gateway.providers.base_image_generation_provider import (
    BaseImageGenerationProvider,
)
from language_model_gateway.gateway.schema.openai.image_generation import (
    ImageGenerationRequest,
)


class ImageGenerationManager:
    def __init__(
        self, *, image_generation_provider: BaseImageGenerationProvider
    ) -> None:
        self.image_generation_provider: BaseImageGenerationProvider = (
            image_generation_provider
        )
        if self.image_generation_provider is None:
            raise ValueError("image_generation_provider must not be None")

    async def generate_image_async(
        self,
        *,
        image_generation_request: ImageGenerationRequest,
        headers: Dict[str, str],
    ) -> StreamingResponse | JSONResponse:
        """
        Implements the image generation manager
        https://platform.openai.com/docs/api-reference/images/create


        :param headers:
        :param image_generation_request:
        :return:
        """
        if image_generation_request is None:
            raise ValueError("image_generation_request must not be None")
        if headers is None:
            raise ValueError("headers must not be None")
        if not isinstance(headers, dict):
            raise TypeError(f"headers must be dict, got {type(headers)}")
        if not isinstance(image_generation_request, dict):
            raise TypeError(
                f"image_generation_request must be dict, got {type(image_generation_request)}"
            )

        response: (
            StreamingResponse | JSONResponse
        ) = await self.image_generation_provider.generate_image_async(
            image_generation_request=image_generation_request, headers=headers
        )

        return response
