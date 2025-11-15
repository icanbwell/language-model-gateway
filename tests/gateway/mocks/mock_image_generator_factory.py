from typing import override

from language_model_gateway.gateway.image_generation.image_generator import (
    ImageGenerator,
)
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)


class MockImageGeneratorFactory(ImageGeneratorFactory):
    def __init__(self, *, image_generator: ImageGenerator) -> None:
        # noinspection PyTypeChecker
        super().__init__(aws_client_factory=None)  # type: ignore[arg-type]
        self.image_generator: ImageGenerator = image_generator
        assert self.image_generator is not None
        assert isinstance(self.image_generator, ImageGenerator)

    @override
    def get_image_generator(self, *, model_name: str) -> ImageGenerator:
        return self.image_generator
