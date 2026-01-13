import json
import logging
import os
from typing import List, Any, Dict, cast, Literal

import boto3
from boto3 import Session
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from types_boto3_bedrock_runtime.client import BedrockRuntimeClient

from language_model_gateway.configs.config_schema import (
    ModelConfig,
    ModelParameterConfig,
    ChatModelConfig,
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
        model_name: str = model_config.model

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
        elif model_config.provider == "google":
            scoped_credentials = self.get_google_credentials()
            model_parameters_dict["credentials"] = scoped_credentials
            llm = ChatGoogleGenerativeAI(**model_parameters_dict)
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
            llm = ChatBedrockConverse(
                client=bedrock_client,
                provider="anthropic",
                credentials_profile_name=aws_credentials_profile,
                region_name=aws_region_name,
                # Setting temperature to 0 for deterministic results
                **model_parameters_dict,
            )
        elif model_config.provider == "openai":
            llm = ChatOpenAI(**model_parameters_dict)
        else:
            raise ValueError(
                f"Unsupported model vendor: {model_vendor} and model_provider: {model_config.provider} for {model_name}"
            )

        return llm

    @staticmethod
    def get_google_credentials() -> Credentials:
        service_account_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not service_account_json:
            raise RuntimeError(
                "GOOGLE_CREDENTIALS_JSON env var not set. Please set the environment variable with your service account JSON."
            )
        try:
            creds_info = json.loads(service_account_json)
        except json.JSONDecodeError:
            raise RuntimeError(
                "GOOGLE_CREDENTIALS_JSON is not valid JSON. Please check the formatting of your credentials."
            )
        logger.debug(f"GOOGLE_CREDENTIALS_JSON: {creds_info}")
        required_fields = ["client_email", "private_key", "project_id"]
        missing_fields = [
            field for field in required_fields if field not in creds_info
        ]
        if missing_fields:
            raise RuntimeError(
                f"Missing required fields in credentials: {', '.join(missing_fields)}. Please check your service account JSON."
            )
        creds: Credentials = service_account.Credentials.from_service_account_info(
            creds_info
        )  # type: ignore[no-untyped-call]
        scoped_credentials: Credentials = creds.with_scopes(
            ["https://www.googleapis.com/auth/cloud-platform"]
        )
        return scoped_credentials
