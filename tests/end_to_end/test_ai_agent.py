import json
from typing import Any, Dict, List

import httpx
import pytest
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletion,
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion import Choice
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig, ModelConfig
from language_model_gateway.gateway.auth.models.auth import AuthInformation
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.providers.openai_chat_completions_provider import (
    OpenAiChatCompletionsProvider,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.structures.openai.request.chat_completion_api_request_wrapper import (
    ChatCompletionApiRequestWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_http_client_factory import MockHttpClientFactory
from tests.gateway.mocks.mock_open_ai_completions_provider import (
    MockOpenAiChatCompletionsProvider,
)


@pytest.mark.asyncio
async def test_call_agent_with_input(async_client: httpx.AsyncClient) -> None:
    print("")

    chat_history: List[ChatCompletionMessageParam] = []
    user_message: ChatCompletionMessageParam = ChatCompletionUserMessageParam(
        role="user",
        content="Have I taken covid vaccine?",
    )
    # Create a ChatRequest object
    model = "General Purpose"
    chat_request_wrapper = ChatCompletionApiRequestWrapper(
        chat_request=ChatRequest(
            model=model,
            messages=chat_history + [user_message],
        )
    )

    provider: OpenAiChatCompletionsProvider
    if EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        provider = OpenAiChatCompletionsProvider(
            http_client_factory=MockHttpClientFactory(
                fn_http_client=lambda: async_client
            )
        )
    else:

        def mock_fn_get_response(
            model_config: ChatModelConfig,
            headers: Dict[str, str],
            chat_request_wrapper: ChatRequestWrapper,
        ) -> Dict[str, Any]:
            chat_response: ChatCompletion = ChatCompletion(
                id="chat_1",
                object="chat.completion",
                created=1633660000,
                model=model,
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content="Yes, you have taken the covid vaccine.",
                            role="assistant",
                        ),
                    )
                ],
            )
            return chat_response.model_dump()

        provider = MockOpenAiChatCompletionsProvider(
            http_client_factory=HttpClientFactory(),
            fn_get_response=mock_fn_get_response,
        )

    response: StreamingResponse | JSONResponse = await provider.chat_completions(
        headers={},
        chat_request_wrapper=chat_request_wrapper,
        model_config=ChatModelConfig(
            id="1",
            name=model,
            description="test model",
            type="chat",
            model=ModelConfig(
                provider="openai",
                model="gpt-3.5-turbo",
            ),
            url="http://localhost:5000/api/v1/chat/completions",
        ),
        auth_information=AuthInformation(
            redirect_uri=None,
            claims=None,
            expires_at=None,
            audience=None,
            email=None,
            subject=None,
            user_name=None,
        ),
    )

    assert response.status_code == 200, response.body
    assert isinstance(response, JSONResponse)
    response_json: str = response.body.decode("utf-8")  # type: ignore[union-attr]
    response_dict: Dict[str, Any] = json.loads(response_json)
    assert "choices" in response_dict
    assert len(response_dict["choices"]) > 0
    assert response_dict["choices"][0]["message"]["content"] is not None
