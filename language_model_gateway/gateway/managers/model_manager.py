import logging
import time
from typing import Dict, List, Any

from openai.types import Model

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ModelManager:
    def __init__(self, *, config_reader: ConfigReader) -> None:
        self.config_reader: ConfigReader = config_reader
        if self.config_reader is None:
            raise ValueError("config_reader must not be None")
        if not isinstance(self.config_reader, ConfigReader):
            raise TypeError(
                f"config_reader must be ConfigReader, got {type(self.config_reader)}"
            )

    # noinspection PyMethodMayBeStatic
    async def get_models(
        self,
        *,
        headers: Dict[str, str],
    ) -> Dict[str, str | List[Dict[str, str | int]]]:
        configs: List[
            ChatModelConfig
        ] = await self.config_reader.read_model_configs_async()

        logger.info("Received request for models")
        # get time in seconds since epoch from ten minutes ago

        models: List[Model] = [
            Model(
                id=config.name,
                created=int(time.time()),
                object="model",
                owned_by="openai",
            )
            for config in configs
        ]
        models_list: List[Dict[str, Any]] = [model.model_dump() for model in models]
        return {"object": "list", "data": models_list}
