import json
import logging
import os
import time
from typing import Dict, List, cast, AsyncGenerator, Optional

from fastapi import HTTPException
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionChunk,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.configs.config_schema import ChatModelConfig, PromptConfig
from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.auth import AuthInformation
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
from language_model_gateway.gateway.structures.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.chat_request_wrapper import (
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
        config_reader: ConfigReader,
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
        self.config_reader: ConfigReader = config_reader
        if self.config_reader is None:
            raise ValueError("config_reader must not be None")
        if not isinstance(self.config_reader, ConfigReader):
            raise TypeError(
                f"config_reader must be ConfigReader, got {type(self.config_reader)}"
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

            chat_request_wrapper = self.add_system_messages(
                chat_request_wrapper=chat_request_wrapper,
                system_prompts=model_config.system_prompts,
            )

            provider: BaseChatCompletionsProvider | None = None
            match model_config.type:
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
                    chat_request_wrapper=chat_request_wrapper,
                    model=model,
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
                chat_request_wrapper=chat_request_wrapper,
                response_messages=[
                    ChatCompletionMessage(role="assistant", content=line.strip())
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
                            headers=first_exception.headers
                        )
                    )
                    content: str = f"Please login at {url} to access the MCP tool from {first_exception.url}."
                    return self.write_response(
                        chat_request_wrapper=chat_request_wrapper,
                        response_messages=[
                            ChatCompletionMessage(role="assistant", content=content)
                        ],
                    )
                elif isinstance(first_exception, AuthorizationNeededException):
                    return self.write_response(
                        chat_request_wrapper=chat_request_wrapper,
                        response_messages=[
                            ChatCompletionMessage(
                                role="assistant", content=line.strip()
                            )
                            for line in first_exception.message.splitlines()
                            if line.strip()
                        ],
                    )
                logger.error(
                    f"ExceptionGroup in chat completion: {first_exception}",
                    exc_info=True,
                )
                return await self.handle_exception(
                    chat_request_wrapper=chat_request_wrapper, e=first_exception
                )
            return await self.handle_exception(
                chat_request_wrapper=chat_request_wrapper, e=e
            )
        except Exception as e:
            return await self.handle_exception(
                chat_request_wrapper=chat_request_wrapper, e=e
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
                ChatMessageWrapper.create_system_message(content=message.content)
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
        chat_request_wrapper: ChatRequestWrapper,
        model: str,
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

        last_message_content: str = cast(str, user_messages[-1].content)
        if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
            logger.info(
                f"Last message content: {last_message_content}, type: {type(last_message_content)}"
            )

        help_keywords: List[str] = os.environ.get("HELP_KEYWORDS", "help").split(";")
        if (
            isinstance(last_message_content, str)
            and last_message_content.lower() in help_keywords
        ):
            logger.info(f"Help requested for model {model}")
            response_messages: List[ChatCompletionMessage] = [
                ChatCompletionMessage(
                    role="assistant",
                    content=model_config.description or "No description available",
                )
            ]
            if model_config.owner is not None:
                response_messages.append(
                    ChatCompletionMessage(
                        role="assistant", content=f"Model owner: {model_config.owner}"
                    )
                )
            if model_config.example_prompts is not None:
                response_messages.append(
                    ChatCompletionMessage(
                        role="assistant", content="Here are some example prompts:"
                    )
                )
                response_messages.extend(
                    [
                        ChatCompletionMessage(role="assistant", content=prompt.content)
                        for prompt in model_config.example_prompts
                    ]
                )

            return self.write_response(
                chat_request_wrapper=chat_request_wrapper,
                response_messages=response_messages,
            )

        return None

    # noinspection PyMethodMayBeStatic
    def write_response(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        response_messages: List[ChatCompletionMessage],
    ) -> StreamingResponse | JSONResponse:
        chat_model: str = chat_request_wrapper.model
        should_stream_response: Optional[bool] = chat_request_wrapper.stream

        if should_stream_response:

            async def stream_response(
                response_messages1: List[ChatCompletionMessage],
            ) -> AsyncGenerator[str, None]:
                for response_message in response_messages1:
                    if response_message.content:
                        chat_stream_response: ChatCompletionChunk = ChatCompletionChunk(
                            id="1",
                            created=int(time.time()),
                            model=chat_model,
                            choices=[
                                ChunkChoice(
                                    index=0,
                                    delta=ChoiceDelta(
                                        role="assistant",
                                        content=response_message.content + "\n",
                                    ),
                                )
                            ],
                            usage=CompletionUsage(
                                prompt_tokens=0,
                                completion_tokens=0,
                                total_tokens=0,
                            ),
                            object="chat.completion.chunk",
                        )
                        yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                content=stream_response(response_messages1=response_messages),
                media_type="text/event-stream",
            )
        else:
            choices: List[Choice] = [
                Choice(index=i, message=m, finish_reason="stop")
                for i, m in enumerate(response_messages)
            ]
            chat_response: ChatCompletion = ChatCompletion(
                id="1",
                model=chat_model,
                choices=choices,
                usage=CompletionUsage(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                ),
                created=int(time.time()),
                object="chat.completion",
            )
            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                logger.info(f"Returning help response: {chat_response.model_dump()}")

            return JSONResponse(content=chat_response.model_dump())

    async def handle_exception(
        self, *, chat_request_wrapper: ChatRequestWrapper, e: Exception
    ) -> StreamingResponse | JSONResponse:
        logger.error(
            f"Error in chat completion: {e} {type(e)} {e.__dict__.keys()}",
            exc_info=True,
        )
        content = ExceptionLogger.extract_error_details(e)
        return self.write_response(
            chat_request_wrapper=chat_request_wrapper,
            response_messages=[
                ChatCompletionMessage(role="assistant", content=content)
            ],
        )
