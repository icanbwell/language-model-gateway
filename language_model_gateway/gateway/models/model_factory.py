import logging
import os
from typing import List, Any, Dict, cast, Literal

import boto3
from boto3 import Session
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from types_boto3_bedrock_runtime.client import BedrockRuntimeClient

from language_model_gateway.configs.config_schema import (
    ModelConfig,
    ModelParameterConfig,
    ChatModelConfig,
)
from language_model_gateway.gateway.langchain_overrides.bedrock_converse_with_logging import (
    ChatBedrockConverseWithLogging,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from botocore.config import Config as BotoConfig

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ModelFactory:
    # noinspection PyMethodMayBeStatic
    def get_model(self, chat_model_config: ChatModelConfig) -> BaseChatModel:
        if chat_model_config is None:
            raise ValueError("chat_model_config must not be None")
        if not isinstance(chat_model_config, ChatModelConfig):
            raise TypeError(
                f"chat_model_config must be ChatModelConfig, got {type(chat_model_config)}"
            )
        model_config: ModelConfig | None = chat_model_config.model
        if model_config is None:
            # if no model configuration is provided, use the default model
            default_model_provider: str = os.environ.get(
                "DEFAULT_MODEL_PROVIDER", "bedrock"
            )
            default_model_name: str = os.environ.get(
                "DEFAULT_MODEL_NAME", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
            )
            model_config = ModelConfig(
                provider=default_model_provider, model=default_model_name
            )

        model_vendor: str = model_config.provider
        model_name: str | None = model_config.model

        model_parameters: List[ModelParameterConfig] | None = (
            chat_model_config.model_parameters
        )

        # convert model_parameters to dict
        model_parameters_dict: Dict[str, Any] = {}
        if model_parameters is not None:
            model_parameter: ModelParameterConfig
            for model_parameter in model_parameters:
                model_parameters_dict[model_parameter.key] = model_parameter.value

        logger.debug(f"Creating ChatModel with parameters: {model_parameters_dict}")
        model_parameters_dict["model"] = model_name
        # model_parameters_dict["streaming"] = True
        llm: BaseChatModel
        if model_vendor == "openai":
            llm = ChatOpenAI(**model_parameters_dict)
        elif model_config.provider == "bedrock":
            retries: dict[str, Literal["legacy", "standard", "adaptive"] | int] = {
                "max_attempts": int(os.getenv("AWS_BEDROCK_MAX_RETRIES", "1")),
                "mode": cast(
                    Literal["legacy", "standard", "adaptive"],
                    os.getenv("AWS_BEDROCK_RETRY_MODE", "standard"),
                ),
            }
            # Specify retries and timeouts for boto3 client
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/config.html
            config = BotoConfig(
                retries=retries,  # type: ignore[arg-type]
                connect_timeout=5,
                read_timeout=20,
            )
            aws_credentials_profile = os.environ.get("AWS_CREDENTIALS_PROFILE")
            aws_region_name = os.environ.get("AWS_REGION", "us-east-1")
            session: Session = boto3.Session(
                profile_name=aws_credentials_profile,
                region_name=aws_region_name,
            )
            bedrock_client: BedrockRuntimeClient = session.client(
                service_name="bedrock-runtime",
                config=config,
                region_name=aws_region_name,
            )
            llm = ChatBedrockConverseWithLogging(
                client=bedrock_client,
                provider="anthropic",
                credentials_profile_name=aws_credentials_profile,
                region_name=aws_region_name,
                # Setting temperature to 0 for deterministic results
                **model_parameters_dict,
            )
        elif model_config.provider == "openai":
            llm = ChatOpenAI(**model_parameters_dict)
        elif model_config.provider == "ollama":
            ollama_base_url = os.getenv("OLLAMA_BASE_URL")
            if not ollama_base_url:
                raise ValueError(
                    "OLLAMA_BASE_URL environment variable must be set for ollama models"
                )
            model_parameters_dict["base_url"] = ollama_base_url
            if (
                "model" not in model_parameters_dict
                or not model_parameters_dict["model"]
            ):
                default_ollama_model = os.getenv("DEFAULT_OLLAMA_MODEL")
                if not default_ollama_model:
                    raise ValueError(
                        "DEFAULT_OLLAMA_MODEL environment variable must be set for ollama models"
                    )
                model_parameters_dict["model"] = default_ollama_model
            llm = ChatOllama(**model_parameters_dict)
        else:
            raise ValueError(
                f"Unsupported model vendor: {model_vendor} and model_provider: {model_config.provider} for {model_name}"
            )

        return llm
