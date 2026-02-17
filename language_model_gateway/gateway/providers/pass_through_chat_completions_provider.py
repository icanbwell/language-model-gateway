import json
import logging
import os
import time
from typing import Dict, Optional, AsyncGenerator, override, List

import httpx
from fastmcp.client import BearerAuth
from httpx import Timeout
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from oidcauthlib.auth.models.auth import AuthInformation
from openai import AsyncOpenAI, AsyncStream, OpenAIError
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionMessage,
    ChatCompletionUserMessageParam,
)
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.logger.logging_transport import (
    LoggingTransport,
)
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice
from openai.types.chat.chat_completion import Choice, ChatCompletion

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["BAILEY"])

DEFAULT_PASSTHROUGH_TIMEOUT_SECONDS: float = 60.0
CONNECT_TIMEOUT_SECONDS: float = 5.0
WRITE_TIMEOUT_SECONDS: float = 5.0


class PassThroughChatCompletionsProvider(BaseChatCompletionsProvider):
    """
    A chat completions provider that simply passes through the request to the another chat completion API
    without any modifications or additional processing.
    This provider can be used when you want to directly forward the chat completion requests to an external API
    """

    def __init__(self, *, pass_through_token_manager: PassThroughTokenManager) -> None:
        self.pass_through_token_manager: PassThroughTokenManager = (
            pass_through_token_manager
        )
        if self.pass_through_token_manager is None:
            raise ValueError("pass_through_token_manager must not be None")
        if not isinstance(self.pass_through_token_manager, PassThroughTokenManager):
            raise TypeError(
                "pass_through_token_manager must be an instance of PassThroughTokenManager"
            )

    @override
    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request_wrapper: ChatRequestWrapper,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse:
        pass_through_url: Optional[str] = model_config.url
        if pass_through_url is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Pass through URL is not configured for this model."},
            )
        if model_config.model is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Model configuration is not provided for this model."
                },
            )

        logger.info(
            f"Forwarding chat completion request to pass through URL: {pass_through_url} with model: {model_config.model.model}"
        )
        # check if we have a valid auth token
        auth_header: str | None = headers.get("Authorization") or headers.get(
            "authorization"
        )
        token: TokenCacheItem | None = None
        if model_config.auth_config is not None:
            if auth_header is None:
                logger.warning(
                    "Authorization header missing for pass through model %s",
                    model_config.model.model,
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Authorization header is required to access this pass through model."
                    },
                )
            try:
                token = await self.pass_through_token_manager.check_tokens_are_valid_for_tool(
                    auth_header=auth_header,
                    auth_information=auth_information,
                    authentication_config=model_config.auth_config,
                )
            except AuthorizationNeededException as e:
                return self.write_response(
                    chat_request_wrapper=chat_request_wrapper,
                    response_messages=[
                        ChatCompletionMessage(role="assistant", content=line.strip())
                        for line in e.message.splitlines()
                        if line.strip()
                    ],
                )
            except Exception as e:
                logger.exception(
                    "Failed to validate pass through token for model %s",
                    model_config.model.model,
                )
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": f"{type(e)}: Unable to validate credentials for the pass through model. {e}"
                    },
                )
            if token is None or token.access_token is None:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized. Valid token is required to access the pass through chat completion API."
                    },
                )

        bearer_token: str | None = (
            token.access_token.token if token and token.access_token else None
        )
        auth: httpx.Auth | None = (
            BearerAuth(token=bearer_token) if bearer_token is not None else None
        )
        timeout_seconds: float = (
            model_config.request_timeout_seconds
            if model_config.request_timeout_seconds is not None
            else DEFAULT_PASSTHROUGH_TIMEOUT_SECONDS
        )
        if timeout_seconds <= 0:
            logger.warning(
                "Invalid timeout %.2f provided for model %s; using default %.2f",
                timeout_seconds,
                model_config.model.model,
                DEFAULT_PASSTHROUGH_TIMEOUT_SECONDS,
            )
            timeout_seconds = DEFAULT_PASSTHROUGH_TIMEOUT_SECONDS
        timeout = Timeout(
            connect=CONNECT_TIMEOUT_SECONDS,
            read=timeout_seconds,
            write=WRITE_TIMEOUT_SECONDS,
            pool=None,
        )
        async_client = httpx.AsyncClient(
            auth=auth,
            timeout=timeout,
            transport=LoggingTransport(httpx.AsyncHTTPTransport()),
        )

        client = AsyncOpenAI(
            api_key="fake-api-key",  # pragma: allowlist secret
            # this api key is ignored for now.  suggest setting it to something that identifies your calling code
            base_url=pass_through_url,
            http_client=async_client,
        )
        # messages: list[ChatCompletionMessageParam] = [
        #     m.to_chat_completion_message() for m in chat_request_wrapper.messages
        # ]
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionUserMessageParam(
                role="user",
                content="show vitals for person id 31c718e9-a3d0-400f-8d95-5bcd9ece5c09",
            )
        ]
        upstream_streaming_enabled: bool = (
            model_config.streaming_enabled
            if model_config.streaming_enabled is not None
            else False
        )
        stream: AsyncStream[ChatCompletionChunk] | None = None
        completion: ChatCompletion | None = None
        try:
            if upstream_streaming_enabled:
                stream = await client.chat.completions.create(
                    messages=messages,
                    model=model_config.model.model,
                    stream=True,
                )
            else:
                completion = await client.chat.completions.create(
                    messages=messages,
                    model=model_config.model.model,
                    stream=False,
                )
        except (OpenAIError, httpx.HTTPError) as e:
            logger.exception(
                "Pass through provider failed to start stream for model %s",
                model_config.model.model,
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": f"{type(e)}: Pass through model failed to start {'streaming' if upstream_streaming_enabled else ''} response from {pass_through_url}. {e}"
                },
            )
        except Exception as e:
            logger.exception(
                "Unexpected error when calling pass through model %s",
                model_config.model.model,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"{type(e)}: Unexpected error occurred when calling the pass through model from {pass_through_url} {'streaming' if upstream_streaming_enabled else ''}. {e}"
                },
            )

        if not upstream_streaming_enabled:
            response_messages: List[ChatCompletionMessage] = (
                [
                    choice.message
                    for choice in completion.choices
                    if choice.message is not None
                ]
                if completion and completion.choices
                else []
            )
            if not response_messages:
                logger.warning(
                    "Pass through model %s returned no messages; emitting raw payload",
                    model_config.model.model,
                )
                response_messages = (
                    [
                        ChatCompletionMessage(
                            role="assistant",
                            content=json.dumps(completion.model_dump()),
                        )
                    ]
                    if completion is not None
                    else []
                )
            return self.write_response(
                chat_request_wrapper=chat_request_wrapper,
                response_messages=response_messages,
            )

        async def stream_response(
            stream1: AsyncStream[ChatCompletionChunk],
        ) -> AsyncGenerator[str, None]:
            try:
                chunk: ChatCompletionChunk
                async for chunk in stream1:
                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"
            except (OpenAIError, httpx.HTTPError):
                logger.exception(
                    "Pass through streaming interrupted for model %s",
                    model_config.model.model if model_config.model else "unknown",
                )
                yield f"data: {json.dumps({'error': 'Streaming interrupted by upstream provider.'})}\n\n"
            except Exception:
                logger.exception(
                    "Unexpected streaming error for pass through model %s",
                    model_config.model.model if model_config.model else "unknown",
                )
                yield f"data: {json.dumps({'error': 'Streaming interrupted by upstream provider.'})}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        if stream is None:
            logger.error(
                "Pass through streaming enabled for model %s but no stream was returned by the client.",
                model_config.model.model,
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Pass through model did not return a stream as expected. Please check the upstream provider."
                },
            )
        return StreamingResponse(
            content=stream_response(stream1=stream),
            media_type="text/event-stream",
        )

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
