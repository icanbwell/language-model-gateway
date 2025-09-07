import json
import logging
from pathlib import Path

from typing import List


from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["CONFIG"])


class FileConfigReader:
    # noinspection PyMethodMayBeStatic
    def read_model_configs(self, *, config_path: str) -> List[ChatModelConfig]:
        return self._read_model_configs(config_path)

    # noinspection PyMethodMayBeStatic
    def _read_model_configs(self, config_path: str) -> List[ChatModelConfig]:
        logger.info(f"Reading model configurations from {config_path}")
        config_folder: Path = Path(config_path)
        # read all the .json files recursively in the config folder
        # for each file, parse the json data into ModelConfig
        configs: List[ChatModelConfig] = []
        # Read all the .json files recursively in the config folder
        for json_file in config_folder.rglob("*.json"):
            with open(json_file, "r") as file:
                data = json.load(file)
                configs.append(ChatModelConfig(**data))
        # sort the configs by name
        configs.sort(key=lambda x: x.name)
        return configs
