from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Optional, override
import json
import logging
from random import randint

from httpx import Response
from httpx_sse import aconnect_sse
from oidcauthlib.auth.models.auth import AuthInformation
from openai.types.chat import (
    ChatCompletion,
)
from pydantic_core import ValidationError
from starlette.responses import StreamingResponse, JSONResponse

from languagemodelcommon.configs.schemas.config_schema import ChatModelConfig
from languagemodelcommon.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from languagemodelcommon.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

if TYPE_CHECKING:
    from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
        LanguageModelGatewayEnvironmentVariables,
    )

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class OpenAiChatCompletionsProvider(BaseChatCompletionsProvider):
    def __init__(
        self,
        *,
        http_client_factory: HttpClientFactory,
        environment_variables: LanguageModelGatewayEnvironmentVariables | None = None,
    ) -> None:
        self.http_client_factory: HttpClientFactory = http_client_factory
        if self.http_client_factory is None:
            raise ValueError("http_client_factory must not be None")
        if not isinstance(self.http_client_factory, HttpClientFactory):
            raise TypeError(
                "http_client_factory must be an instance of HttpClientFactory"
            )
        self._environment_variables: LanguageModelGatewayEnvironmentVariables | None = (
            environment_variables
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
        """
        Call the OpenAI API to get chat completions

        :param headers:
        :param chat_request_wrapper:
        :param model_config:
        :param auth_information:

        :return:
        """
        if chat_request_wrapper is None:
            raise ValueError("chat_request must not be None")

        request_id: str = str(randint(1, 1000))
        openai_agent_url: Optional[str] = (
            self._environment_variables.openai_agent_url
            if self._environment_variables
            else None
        )
        agent_url: Optional[str] = model_config.url or openai_agent_url
        if not agent_url:
            raise ValueError("agent_url must not be None")

        if chat_request_wrapper.stream:
            return StreamingResponse(
                self._stream_resp_async_generator(
                    agent_url=agent_url,
                    request_id=request_id,
                    chat_request_wrapper=chat_request_wrapper,
                    headers=headers,
                ),
                media_type="text/event-stream",
            )

        response_text: Optional[str] = None
        async with self.http_client_factory.create_http_client(
            base_url="http://test"
        ) as client:
            try:
                agent_response: Response = await client.post(
                    agent_url,
                    json=chat_request_wrapper.to_dict(),
                    timeout=60 * 60,
                    headers=headers,
                )

                response_text = agent_response.text
                response_dict: Dict[str, Any] = agent_response.json()
            except json.JSONDecodeError:
                logger.exception(f"Error decoding response. url: {agent_url}")
                return JSONResponse(
                    content=f"Error decoding response. url: {agent_url}\n{response_text}",
                    status_code=500,
                )
            except Exception as e:
                logger.exception(f"Error from agent: {e} url: {agent_url}")
                return JSONResponse(
                    content=f"Error from agent: {e} url: {agent_url}\n{response_text}",
                    status_code=500,
                )

            try:
                response: ChatCompletion = ChatCompletion.model_validate(response_dict)
            except ValidationError as e:
                return JSONResponse(
                    content=f"Error validating response: {e}. url: {agent_url}\n{response_text}",
                    status_code=500,
                )
            if (
                self._environment_variables
                and self._environment_variables.log_input_and_output
            ):
                logger.info(f"Non-streaming response {request_id}: {response}")
            return JSONResponse(content=response.model_dump())

    async def _stream_resp_async_generator(
        self,
        *,
        request_id: str,
        agent_url: str,
        chat_request_wrapper: ChatRequestWrapper,
        headers: Dict[str, str],
    ) -> AsyncGenerator[str, None]:
        logger.info(f"Streaming response {request_id} from agent")
        try:
            async with self.http_client_factory.create_http_client(
                base_url="http://test"
            ) as client:
                async with aconnect_sse(
                    client,
                    "POST",
                    agent_url,
                    json=chat_request_wrapper.to_dict(),
                    timeout=60 * 60,
                    headers=headers,
                ) as event_source:
                    async for sse in event_source.aiter_sse():
                        data: str = sse.data
                        if (
                            self._environment_variables
                            and self._environment_variables.log_input_and_output
                        ):
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(
                                    f"----- Received SSE {sse.event}: {data} ------"
                                )
                        yield f"data: {data}\n\n"
        except Exception as e:
            logger.error(
                f"Exception in _stream_resp_async_generator: {e}", exc_info=True
            )
            yield f'data: {{"error": "{str(e)}"}}\n\n'
        finally:
            yield "data: [DONE]\n\n"
