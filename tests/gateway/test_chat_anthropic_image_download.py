import os
from pathlib import Path

import httpx
import pytest

from language_model_gateway.configs.config_schema import ChatModelConfig, ModelConfig
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from oidcauthlib.container.interfaces import IContainer


@pytest.mark.asyncio
async def test_chat_anthropic_image_download(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="ChatGPT",
                type="langchain",
                model=ModelConfig(provider="ollama"),
            )
        ]
    )
    file_path = Path(os.environ["IMAGE_GENERATION_PATH"]).joinpath("foo.png")
    print(f"Writing to {file_path}")
    with open(file_path, "wb") as f:
        f.write(b"image content")
    response = await async_client.request(
        "GET",
        "http://localhost:5000/image_generation/foo.png",
    )
    assert response.status_code == 200, f"Response content: {response.content!r}"
    assert response.content == b"image content"
    print(response.content)
