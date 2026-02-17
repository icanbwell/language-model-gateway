import datetime
import logging
import uuid
from typing import (
    Dict,
    Any,
    Sequence,
    AsyncGenerator,
    ContextManager,
    override,
)
from starlette.responses import StreamingResponse, JSONResponse

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from language_model_gateway.configs.config_schema import ChatModelConfig, AgentConfig
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.token_reader import TokenReader

from language_model_gateway.gateway.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.persistence.persistence_factory import (
    PersistenceFactory,
)
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.mcp.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from langgraph.store.base import BaseStore
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangChainCompletionsProvider(BaseChatCompletionsProvider):
    def __init__(
        self,
        *,
        model_factory: ModelFactory,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
        token_reader: TokenReader,
        pass_through_token_manager: PassThroughTokenManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        persistence_factory: PersistenceFactory,
    ) -> None:
        self.model_factory: ModelFactory = model_factory
        if self.model_factory is None:
            raise ValueError("model_factory must not be None")
        if not isinstance(self.model_factory, ModelFactory):
            raise TypeError("model_factory must be an instance of ModelFactory")
        self.lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter = (
            lang_graph_to_open_ai_converter
        )
        if self.lang_graph_to_open_ai_converter is None:
            raise ValueError("lang_graph_to_open_ai_converter must not be None")
        if not isinstance(
            self.lang_graph_to_open_ai_converter, LangGraphToOpenAIConverter
        ):
            raise TypeError(
                "lang_graph_to_open_ai_converter must be an instance of LangGraphToOpenAIConverter"
            )
        self.tool_provider: ToolProvider = tool_provider
        if self.tool_provider is None:
            raise ValueError("tool_provider must not be None")
        if not isinstance(self.tool_provider, ToolProvider):
            raise TypeError("tool_provider must be an instance of ToolProvider")

        self.mcp_tool_provider: MCPToolProvider = mcp_tool_provider
        if self.mcp_tool_provider is None:
            raise ValueError("mcp_tool_provider must not be None")
        if not isinstance(self.mcp_tool_provider, MCPToolProvider):
            raise TypeError("mcp_tool_provider must be an instance of MCPToolProvider")

        self.token_reader: TokenReader = token_reader
        if self.token_reader is None:
            raise ValueError("token_reader must not be None")
        if not isinstance(self.token_reader, TokenReader):
            raise TypeError("token_reader must be an instance of TokenReader")

        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "environment_variables must be an instance of EnvironmentVariables"
            )

        self.persistence_factory: PersistenceFactory = persistence_factory
        if self.persistence_factory is None:
            raise ValueError("persistence_factory must not be None")
        if not isinstance(self.persistence_factory, PersistenceFactory):
            raise TypeError(
                "persistence_factory must be an instance of PersistenceFactory"
            )

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
        # noinspection PyArgumentList
        llm: BaseChatModel = self.model_factory.get_model(
            chat_model_config=model_config
        )

        # noinspection PyUnusedLocal
        def get_current_time(*args: Any, **kwargs: Any) -> str:
            """Returns the current time in H:MM AM/PM format."""
            now = datetime.datetime.now()  # Get current time
            return now.strftime("%Y-%m-%d %H:%M:%S%Z%z")

        # Initialize tools
        tools: Sequence[BaseTool] = (
            self.tool_provider.get_tools(
                tools=[t for t in model_config.get_agents()], headers=headers
            )
            if model_config.get_agents() is not None
            else []
        )

        # Load MCP tools if they are enabled
        await self.mcp_tool_provider.load_async()
        await self.pass_through_token_manager.check_tokens_are_valid_for_tools(
            auth_information=auth_information,
            headers=headers,
            model_config=model_config,
        )

        # add MCP tools
        tools = [t for t in tools] + await self.mcp_tool_provider.get_tools_async(
            tools=[t for t in model_config.get_agents()],
            headers=headers,
        )

        # finally read any tools from the Responses API request
        tool_configs_from_request: list[AgentConfig] = chat_request_wrapper.get_tools()
        if tool_configs_from_request:
            tools_from_request: Sequence[BaseTool] = (
                await self.mcp_tool_provider.get_tools_async(
                    tools=tool_configs_from_request, headers=headers
                )
                if tool_configs_from_request is not None
                else []
            )
            tools = [t for t in tools] + [t for t in tools_from_request]

        # Use context managers only for the duration of streaming
        # we can't use async with because we need to return the StreamingResponse
        store_cm: ContextManager[BaseStore] = self.persistence_factory.create_store(
            persistence_type=self.environment_variables.llm_storage_type,
        )
        checkpointer_cm: ContextManager[BaseCheckpointSaver[str]] = (
            self.persistence_factory.create_checkpointer(
                persistence_type=self.environment_variables.llm_storage_type,
            )
        )
        try:
            store = store_cm.__enter__()
            checkpointer = checkpointer_cm.__enter__()
            compiled_state_graph: CompiledStateGraph[
                MyMessagesState
            ] = await self.lang_graph_to_open_ai_converter.create_graph_for_llm_async(
                llm=llm,
                tools=tools,
                store=store if self.environment_variables.enable_llm_store else None,
                checkpointer=checkpointer
                if self.environment_variables.enable_llm_checkpointer
                else None,
            )
            request_id: uuid.UUID = uuid.uuid4()

            conversation_thread_id: str | None = headers.get("X-Chat-Id".lower())

            result = await self.lang_graph_to_open_ai_converter.call_agent_with_input(
                compiled_state_graph=compiled_state_graph,
                chat_request_wrapper=chat_request_wrapper,
                system_messages=[],
                request_information=RequestInformation(
                    auth_information=auth_information,
                    user_id=auth_information.subject,
                    user_email=auth_information.email,
                    user_name=auth_information.user_name,
                    request_id=str(request_id),
                    conversation_thread_id=conversation_thread_id
                    if conversation_thread_id
                    else str(request_id),
                    headers=headers,
                ),
            )
            # If result is a StreamingResponse, wrap the generator so context managers stay open
            if isinstance(result, StreamingResponse):
                original_generator = result.body_iterator

                async def streaming_wrapper() -> AsyncGenerator[
                    str | bytes | memoryview, None
                ]:
                    try:
                        async for chunk in original_generator:
                            yield chunk
                    finally:
                        checkpointer_cm.__exit__(None, None, None)
                        store_cm.__exit__(None, None, None)

                result.body_iterator = streaming_wrapper()
                return result
            else:
                checkpointer_cm.__exit__(None, None, None)
                store_cm.__exit__(None, None, None)
                return result
        except Exception as e:
            checkpointer_cm.__exit__(type(e), e, e.__traceback__)
            store_cm.__exit__(type(e), e, e.__traceback__)
            raise
