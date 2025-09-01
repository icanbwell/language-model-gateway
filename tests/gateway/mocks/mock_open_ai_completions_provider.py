from typing import Dict, Any

from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.auth.models.auth import AuthInformation
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.providers.openai_chat_completions_provider import (
    OpenAiChatCompletionsProvider,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from tests.gateway.mocks.mock_chat_response import MockChatResponseProtocol


class MockOpenAiChatCompletionsProvider(OpenAiChatCompletionsProvider):
    def __init__(
        self,
        *,
        http_client_factory: HttpClientFactory,
        fn_get_response: MockChatResponseProtocol,
    ) -> None:
        super().__init__(http_client_factory=http_client_factory)
        self.fn_get_response: MockChatResponseProtocol = fn_get_response

    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request: ChatRequest,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse:
        result: Dict[str, Any] = self.fn_get_response(
            model_config=model_config,
            headers=headers,
            chat_request=chat_request,
        )
        return JSONResponse(content=result)
