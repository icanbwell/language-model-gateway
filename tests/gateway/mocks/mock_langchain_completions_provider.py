from typing import Dict, Any

from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.models.auth import AuthInformation
from language_model_gateway.gateway.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.providers.langchain_chat_completions_provider import (
    LangChainCompletionsProvider,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.tools.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.auth.token_reader import TokenReader
from tests.gateway.mocks.mock_chat_response import MockChatResponseProtocol


class MockLangChainChatCompletionsProvider(LangChainCompletionsProvider):
    def __init__(
        self,
        *,
        model_factory: ModelFactory,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
        token_verifier: TokenReader,
        auth_manager: AuthManager,
        fn_get_response: MockChatResponseProtocol,
    ) -> None:
        super().__init__(
            model_factory=model_factory,
            lang_graph_to_open_ai_converter=lang_graph_to_open_ai_converter,
            tool_provider=tool_provider,
            mcp_tool_provider=mcp_tool_provider,
            token_verifier=token_verifier,
            auth_manager=auth_manager,
        )
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
