import base64
import logging
import os
import time
from typing import Dict, List, Literal, Optional, Union
from uuid import uuid4

from openai import NotGiven
from openai.types import ImagesResponse, Image, ImageModel
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.gateway.file_managers.file_saver import FileSaver
from language_model_gateway.gateway.image_generation.image_generator import (
    ImageGenerator,
)
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.providers.base_image_generation_provider import (
    BaseImageGenerationProvider,
)
from language_model_gateway.gateway.schema.openai.image_generation import (
    ImageGenerationRequest,
)

logger = logging.getLogger(__name__)


class ImageGenerationProvider(BaseImageGenerationProvider):
    def __init__(
        self, *, image_generator_factory: ImageGeneratorFactory, file_saver: FileSaver
    ) -> None:
        self.image_generator_factory: ImageGeneratorFactory = image_generator_factory
        assert self.image_generator_factory is not None
        assert isinstance(self.image_generator_factory, ImageGeneratorFactory)
        self.file_saver: FileSaver = file_saver
        assert self.file_saver is not None
        assert isinstance(self.file_saver, FileSaver)

    async def generate_image_async(
        self,
        *,
        image_generation_request: ImageGenerationRequest,
        headers: Dict[str, str],
    ) -> StreamingResponse | JSONResponse:
        """
        Implements the image generation API
        https://platform.openai.com/docs/api-reference/images/create

        :param image_generation_request:
        :param headers:
        :return:
        """
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = (
            image_generation_request.get("response_format")
        )

        logger.info(f"image_generation_request: {image_generation_request}")

        model: Union[str, ImageModel, None] | NotGiven = image_generation_request.get(
            "model"
        )

        image_generator: ImageGenerator = (
            self.image_generator_factory.get_image_generator(
                model_name=str(model) if model else "aws"
            )
        )

        prompt = image_generation_request["prompt"]
        assert prompt is not None
        assert isinstance(prompt, str)

        image_bytes: bytes = await image_generator.generate_image_async(prompt=prompt)

        response_data: List[Image]
        if response_format == "b64_json":
            # convert image_bytes to base64 json
            # logger.info(f"image_bytes: {image_bytes!r}")
            image_b64_json = base64.b64encode(image_bytes).decode("utf-8")
            # logger.info(f"image_b64_json: {image_b64_json}")
            response_data = [Image(b64_json=image_b64_json)]
        else:
            image_generation_path_ = os.environ["IMAGE_GENERATION_PATH"]
            assert (
                image_generation_path_
            ), "IMAGE_GENERATION_PATH environment variable is not set"
            image_file_name: str = f"{uuid4()}.png"
            url: Optional[str] = await self.file_saver.save_file_async(
                image_data=image_bytes,
                folder=image_generation_path_,
                filename=image_file_name,
            )
            response_data = [Image(url=url)] if url else []

        response: ImagesResponse = ImagesResponse(
            created=int(time.time()), data=response_data
        )
        return JSONResponse(content=response.model_dump())
