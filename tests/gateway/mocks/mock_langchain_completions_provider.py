from typing import Dict, Any, override

from langchain_ai_skills_framework.loaders.skill_loader_protocol import (
    SkillLoaderProtocol,
)
from languagemodelcommon.utilities.tool_display_name_mapper import (
    ToolDisplayNameMapper,
)
from starlette.responses import StreamingResponse, JSONResponse

from languagemodelcommon.configs.schemas.config_schema import ChatModelConfig
from oidcauthlib.auth.models.auth import AuthInformation

from languagemodelcommon.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from languagemodelcommon.persistence.persistence_factory import (
    PersistenceFactory,
)
from language_model_gateway.gateway.providers.langchain_chat_completions_provider import (
    LangChainCompletionsProvider,
)
from languagemodelcommon.auth.pass_through_token_manager import (
    PassThroughTokenManager,
)
from languagemodelcommon.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from oidcauthlib.auth.token_reader import TokenReader
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from tests.gateway.mocks.mock_chat_response import MockChatResponseProtocol


class MockLangChainChatCompletionsProvider(LangChainCompletionsProvider):
    def __init__(
        self,
        *,
        model_factory: ModelFactory,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
        token_reader: TokenReader,
        pass_through_token_manager: PassThroughTokenManager,
        fn_get_response: MockChatResponseProtocol,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        persistence_factory: PersistenceFactory,
        skill_loader: SkillLoaderProtocol,
        tool_friendly_name_mapper: ToolDisplayNameMapper,
    ) -> None:
        super().__init__(
            model_factory=model_factory,
            lang_graph_to_open_ai_converter=lang_graph_to_open_ai_converter,
            tool_provider=tool_provider,
            mcp_tool_provider=mcp_tool_provider,
            token_reader=token_reader,
            pass_through_token_manager=pass_through_token_manager,
            environment_variables=environment_variables,
            persistence_factory=persistence_factory,
            skill_loader=skill_loader,
            tool_friendly_name_mapper=tool_friendly_name_mapper,
        )
        self.fn_get_response: MockChatResponseProtocol = fn_get_response

    @override
    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request_wrapper: ChatRequestWrapper,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse:
        result: Dict[str, Any] = self.fn_get_response(
            model_config=model_config,
            headers=headers,
            chat_request_wrapper=chat_request_wrapper,
        )
        return JSONResponse(content=result)
