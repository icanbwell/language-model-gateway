import json
import logging
from typing import Dict, Optional, AsyncGenerator, override

import httpx
from fastmcp.client import BearerAuth
from httpx import Timeout
from oidcauthlib.auth.models.auth import AuthInformation
from openai import AsyncOpenAI, AsyncStream, OpenAIError
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
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

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["BAILEY"])


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
        async_client = httpx.AsyncClient(
            auth=auth,
            headers=headers,
            timeout=Timeout(timeout=5.0),
            transport=LoggingTransport(httpx.AsyncHTTPTransport()),
        )

        client = AsyncOpenAI(
            api_key="fake-api-key",  # pragma: allowlist secret
            # this api key is ignored for now.  suggest setting it to something that identifies your calling code
            base_url=pass_through_url,
            http_client=async_client,
            # default_headers={
            #     "Authorization": f"Bearer {token.access_token.token}",
            # }
            # if token and token.access_token and token.access_token.token
            # else {},
        )
        messages: list[ChatCompletionMessageParam] = [
            m.to_chat_completion_message() for m in chat_request_wrapper.messages
        ]
        try:
            stream: AsyncStream[
                ChatCompletionChunk
            ] = await client.chat.completions.create(
                messages=messages,
                model=model_config.model.model,
                stream=True,  # enables streaming
            )
        except (OpenAIError, httpx.HTTPError) as e:
            logger.exception(
                "Pass through provider failed to start stream for model %s",
                model_config.model.model,
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": f"{type(e)}: Pass through model failed to start streaming response from {pass_through_url}. {e}"
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
                    "error": f"{type(e)}: Unexpected error occurred when calling the pass through model from {pass_through_url}. {e}"
                },
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

        return StreamingResponse(
            content=stream_response(stream1=stream),
            media_type="text/event-stream",
        )
