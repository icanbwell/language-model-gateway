import logging
from typing import Literal, Tuple, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from language_model_gateway.gateway.image_generation.image_generator import (
    ImageGenerator,
)
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.utilities.image_generation_helper import (
    ImageGenerationHelper,
)

logger = logging.getLogger(__name__)


class ImageGeneratorToolInput(BaseModel):
    prompt: str = Field(description="Prompt to use for generating the image")


class ImageGeneratorTool(BaseTool):
    """
    LangChain-compatible tool for generating an image from a given text.
    """

    name: str = "image_generator"
    description: str = (
        "Generates an image from a given text. "
        "Provide the text as input. "
        # "The tool will return the image as a base64 encoded string in PNG format: `data:image/png;base64,{base64_image}`."
        "The tool will return a url to the generated image."
    )
    args_schema: Type[BaseModel] = ImageGeneratorToolInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"
    image_generator_factory: ImageGeneratorFactory

    def _run(self, prompt: str) -> Tuple[str, str]:
        """
        Synchronous version of the tool (falls back to async implementation).
        :param prompt: The URL of the webpage to fetch.
        :return: The content of the webpage in Markdown format.
        """
        raise NotImplementedError("Use async version of this tool")

    async def _arun(self, prompt: str) -> Tuple[str, str]:
        """
        Asynchronous version of the tool.
        :param prompt: The URL of the webpage to fetch.
        :return: The content of the webpage in Markdown format.
        """
        try:
            image_generator: ImageGenerator = (
                self.image_generator_factory.get_image_generator(model_name="aws")
            )
            # styles = ["natural", "cinematic", "digital-art", "pop-art"]
            style = "natural"
            image_data: bytes = await image_generator.generate_image_async(
                prompt=prompt, style=style, image_size="1024x1024"
            )
            # base64_image: str = base64.b64encode(image_data).decode("utf-8")
            image_file_path = ImageGenerationHelper.get_full_path()
            await image_generator.save_image_async(image_data, image_file_path)
            url = ImageGenerationHelper.get_url_for_file_name(image_file_path)
            return (
                url,
                f"ImageGeneratorTool: Generated image from prompt: {prompt}: <{url}> ",
            )
        except Exception as e:
            logger.error(f"Failed to generate image: {str(e)}")
            logger.exception(e, stack_info=True)
            return (
                f"Failed to generate image: {e}",
                f"ImageGeneratorTool: Failed to generate image from prompt: {prompt}",
            )
