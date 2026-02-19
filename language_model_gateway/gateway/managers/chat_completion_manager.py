import logging
import os
import uuid
from typing import Dict, List

from fastapi import HTTPException
from httpx import Headers
from langchain_core.messages import AnyMessage, AIMessage
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from oidcauthlib.auth.models.auth import AuthInformation
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.configs.config_schema import ChatModelConfig, PromptConfig
from language_model_gateway.gateway.managers.system_command_manager import (
    SystemCommandManager,
)
from language_model_gateway.gateway.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from language_model_gateway.gateway.mcp.mcp_authorization_helper import (
    McpAuthorizationHelper,
)
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from language_model_gateway.gateway.providers.langchain_chat_completions_provider import (
    LangChainCompletionsProvider,
)
from language_model_gateway.gateway.providers.openai_chat_completions_provider import (
    OpenAiChatCompletionsProvider,
)
from language_model_gateway.gateway.providers.pass_through_chat_completions_provider import (
    PassThroughChatCompletionsProvider,
)
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.exception_logger import ExceptionLogger
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ChatCompletionManager:
    """
    Implements the chat completion manager following the OpenAI API
    https://platform.openai.com/docs/overview
    https://github.com/openai/openai-python/blob/main/api.md
    """

    def __init__(
        self,
        *,
        open_ai_provider: OpenAiChatCompletionsProvider,
        langchain_provider: LangChainCompletionsProvider,
        pass_through_provider: PassThroughChatCompletionsProvider,
        config_reader: ConfigReader,
        system_command_manager: SystemCommandManager,
    ) -> None:
        self.openai_provider: OpenAiChatCompletionsProvider = open_ai_provider
        if self.openai_provider is None:
            raise ValueError("open_ai_provider must not be None")
        if not isinstance(self.openai_provider, OpenAiChatCompletionsProvider):
            raise TypeError(
                f"open_ai_provider must be OpenAiChatCompletionsProvider, got {type(self.openai_provider)}"
            )
        self.langchain_provider: LangChainCompletionsProvider = langchain_provider
        if self.langchain_provider is None:
            raise ValueError("langchain_provider must not be None")
        if not isinstance(self.langchain_provider, LangChainCompletionsProvider):
            raise TypeError(
                f"langchain_provider must be LangChainCompletionsProvider, got {type(self.langchain_provider)}"
            )

        self.pass_through_provider: PassThroughChatCompletionsProvider = (
            pass_through_provider
        )
        if self.pass_through_provider is None:
            raise ValueError("pass_through_provider must not be None")
        if not isinstance(
            self.pass_through_provider, PassThroughChatCompletionsProvider
        ):
            raise TypeError(
                f"pass_through_provider must be PassThroughChatCompletionsProvider, got {type(self.pass_through_provider)}"
            )
        self.config_reader: ConfigReader = config_reader
        if self.config_reader is None:
            raise ValueError("config_reader must not be None")
        if not isinstance(self.config_reader, ConfigReader):
            raise TypeError(
                f"config_reader must be ConfigReader, got {type(self.config_reader)}"
            )

        self.system_command_manager: SystemCommandManager = system_command_manager
        if self.system_command_manager is None:
            raise ValueError("system_command_manager must not be None")
        if not isinstance(self.system_command_manager, SystemCommandManager):
            raise TypeError(
                f"system_command_manager must be SystemCommandManager, got {type(self.system_command_manager)}"
            )

    # noinspection PyMethodMayBeStatic
    async def chat_completions(
        self,
        *,
        headers: Dict[str, str],
        chat_request_wrapper: ChatRequestWrapper,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse:
        # Use the model to choose the provider
        request_id: str = str(uuid.uuid4())
        try:
            model: str = chat_request_wrapper.model
            if model is None:
                raise ValueError("model must not be None in chat_request")

            configs: List[
                ChatModelConfig
            ] = await self.config_reader.read_model_configs_async()

            # Find the model config
            configs = [
                config for config in configs if config.name.lower() == model.lower()
            ]
            model_config: ChatModelConfig | None = (
                configs[0] if len(configs) > 0 else None
            )
            if model_config is None:
                logger.error(f"Model {model} not found in the config")
                raise HTTPException(
                    status_code=400, detail=f"Model {model} not found in the config"
                )

            if auth_information.subject is not None:
                system_response: (
                    StreamingResponse | JSONResponse | None
                ) = await self.system_command_manager.run_system_commands(
                    request_id=request_id,
                    auth_provider=None,  # TODO: pass auth provider if needed for system commands
                    chat_request_wrapper=chat_request_wrapper,
                    referring_subject=auth_information.subject,
                )
                if system_response is not None:
                    return system_response

            chat_request_wrapper = self.add_system_messages(
                chat_request_wrapper=chat_request_wrapper,
                system_prompts=model_config.system_prompts,
            )

            provider: BaseChatCompletionsProvider | None = None
            match model_config.type:
                case "passthru":
                    provider = self.pass_through_provider
                case "openai":
                    provider = self.openai_provider
                case "langchain":
                    provider = self.langchain_provider
                case _:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model type {model_config.type} not supported",
                    )

            if provider is None:
                raise RuntimeError(
                    f"Provider should not be None for model type {model_config.type}"
                )

            help_response: StreamingResponse | JSONResponse | None = (
                self.handle_help_prompt(
                    request_id=request_id,
                    chat_request_wrapper=chat_request_wrapper,
                    model_name=model,
                    model_config=model_config,
                )
            )
            if help_response is not None:
                return help_response

            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                logger.info(
                    f"Running chat completion for {chat_request_wrapper} with headers {headers}"
                )
            # Use the provider to get the completions
            response: (
                StreamingResponse | JSONResponse
            ) = await provider.chat_completions(
                model_config=model_config,
                headers=headers,
                chat_request_wrapper=chat_request_wrapper,
                auth_information=auth_information,
            )
            return response
        except AuthorizationNeededException as e:
            return self.write_response(
                request_id=request_id,
                chat_request_wrapper=chat_request_wrapper,
                response_messages=[
                    AIMessage(content=line.strip())
                    for line in e.message.splitlines()
                    if line.strip()
                ],
            )
        except ExceptionGroup as e:
            # if there is just one exception, we can log it directly
            if len(e.exceptions) == 1:
                first_exception = e.exceptions[0]
                if (
                    isinstance(first_exception, McpToolUnauthorizedException)
                    and first_exception.headers
                ):
                    url: str | None = (
                        McpAuthorizationHelper.extract_resource_metadata_from_www_auth(
                            headers=Headers(first_exception.headers)
                        )
                    )
                    content: str = f"Please login at {url} to access the MCP tool from {first_exception.url}."
                    return self.write_response(
                        request_id=request_id,
                        chat_request_wrapper=chat_request_wrapper,
                        response_messages=[AIMessage(content=content)],
                    )
                elif isinstance(first_exception, AuthorizationNeededException):
                    return self.write_response(
                        request_id=request_id,
                        chat_request_wrapper=chat_request_wrapper,
                        response_messages=[
                            AIMessage(content=line.strip())
                            for line in first_exception.message.splitlines()
                            if line.strip()
                        ],
                    )
                logger.error(
                    f"ExceptionGroup in chat completion: {first_exception}",
                    exc_info=True,
                )
                return await self.handle_exception(
                    request_id=request_id,
                    chat_request_wrapper=chat_request_wrapper,
                    e=first_exception,
                )
            return await self.handle_exception(
                request_id=request_id, chat_request_wrapper=chat_request_wrapper, e=e
            )
        except Exception as e:
            return await self.handle_exception(
                request_id=request_id, chat_request_wrapper=chat_request_wrapper, e=e
            )

    # noinspection PyMethodMayBeStatic
    def add_system_messages(
        self,
        chat_request_wrapper: ChatRequestWrapper,
        system_prompts: List[PromptConfig] | None,
    ) -> ChatRequestWrapper:
        # see if there are any system prompts in chat_request
        has_system_messages_in_chat_request: bool = any(
            [
                message
                for message in chat_request_wrapper.messages
                if message.system_message
            ]
        )
        if (
            not has_system_messages_in_chat_request
            and system_prompts is not None
            and len(system_prompts) > 0
        ):
            system_messages: List[ChatMessageWrapper] = [
                chat_request_wrapper.create_system_message(content=message.content)
                for message in system_prompts
                if message.role == "system" and message.content is not None
            ]
            chat_request_wrapper.messages = system_messages + [
                r for r in chat_request_wrapper.messages
            ]

        return chat_request_wrapper

    # noinspection PyMethodMayBeStatic
    def handle_help_prompt(
        self,
        *,
        request_id: str,
        chat_request_wrapper: ChatRequestWrapper,
        model_name: str,
        model_config: ChatModelConfig,
    ) -> StreamingResponse | JSONResponse | None:
        request_messages: List[ChatMessageWrapper] = [
            m for m in chat_request_wrapper.messages
        ]
        if request_messages is None:
            logger.error("Messages not found in the request")
            raise HTTPException(
                status_code=400, detail="Messages not found in the request"
            )

        user_messages: List[ChatMessageWrapper] = [
            m for m in request_messages if not m.system_message
        ]
        if user_messages is None or len(user_messages) == 0:
            logger.error("User messages not found in the request")
            raise HTTPException(
                status_code=400, detail="User messages not found in the request"
            )

        last_message_content: str | None = user_messages[-1].content
        if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
            logger.info(
                f"Last message content: {last_message_content}, type: {type(last_message_content)}"
            )

        help_keywords: List[str] = os.environ.get("HELP_KEYWORDS", "help").split(";")
        if (
            isinstance(last_message_content, str)
            and last_message_content.lower() in help_keywords
        ):
            logger.info(f"Help requested for model {model_name}: {model_config}")
            response_messages: List[AnyMessage] = [
                AIMessage(
                    content=model_config.description or "No description available",
                )
            ]
            if model_config.owner is not None:
                response_messages.append(
                    AIMessage(content=f"Model owner: {model_config.owner}")
                )
            if (
                model_config.model is not None
                and model_config.model.provider is not None
            ):
                response_messages.append(
                    AIMessage(
                        content=f"Model Provider: {model_config.model.provider}",
                    )
                )
            if model_config.model is not None and model_config.model.model is not None:
                response_messages.append(
                    AIMessage(content=f"Model: {model_config.model.model}")
                )
            if model_config.example_prompts is not None:
                response_messages.append(
                    AIMessage(content="Here are some example prompts:")
                )
                response_messages.extend(
                    [
                        AIMessage(content=prompt.content)
                        for prompt in model_config.example_prompts
                    ]
                )

            return self.write_response(
                request_id=request_id,
                chat_request_wrapper=chat_request_wrapper,
                response_messages=response_messages,
            )

        return None

    # noinspection PyMethodMayBeStatic
    def write_response(
        self,
        *,
        request_id: str,
        chat_request_wrapper: ChatRequestWrapper,
        response_messages: List[AnyMessage],
    ) -> StreamingResponse | JSONResponse:
        return chat_request_wrapper.write_response(
            request_id=request_id,
            response_messages=response_messages,
        )

    async def handle_exception(
        self,
        *,
        request_id: str,
        chat_request_wrapper: ChatRequestWrapper,
        e: Exception,
    ) -> StreamingResponse | JSONResponse:
        logger.error(
            f"Error in chat completion: {e} {type(e)} {e.__dict__.keys()}",
            exc_info=True,
        )
        content = ExceptionLogger.extract_error_details(e)
        return self.write_response(
            request_id=request_id,
            chat_request_wrapper=chat_request_wrapper,
            response_messages=[AIMessage(content=content)],
        )
