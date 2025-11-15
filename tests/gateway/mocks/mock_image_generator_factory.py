from typing import override

from language_model_gateway.gateway.image_generation.image_generator import (
    ImageGenerator,
)
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)


class MockImageGeneratorFactory(ImageGeneratorFactory):
    # noinspection PyMissingConstructor
    def __init__(self, *, image_generator: ImageGenerator) -> None:
        self.image_generator: ImageGenerator = image_generator
        assert self.image_generator is not None
        assert isinstance(self.image_generator, ImageGenerator)

    @override
    def get_image_generator(self, *, model_name: str) -> ImageGenerator:
        return self.image_generator
