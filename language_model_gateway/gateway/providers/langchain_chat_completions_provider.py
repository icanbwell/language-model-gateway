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

from languagemodelcommon.utilities.tool_display_name_mapper import (
    ToolDisplayNameMapper,
)
from starlette.responses import StreamingResponse, JSONResponse

from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from languagemodelcommon.configs.schemas.config_schema import (
    ChatModelConfig,
    AgentConfig,
)
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.token_reader import TokenReader
from language_model_gateway.gateway.managers.model_resource_cache_manager import (
    ModelResourceCacheManager,
)

from languagemodelcommon.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from languagemodelcommon.state.messages_state import MyMessagesState
from languagemodelcommon.persistence.persistence_factory import (
    PersistenceFactory,
)
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from languagemodelcommon.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from languagemodelcommon.mcp.interceptors.auth import (
    AuthMcpCallInterceptor,
)
from languagemodelcommon.mcp.mcp_client.session_pool import McpSessionPool
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider
from languagemodelcommon.tools.mcp.search_tools_tool import SearchToolsTool
from languagemodelcommon.tools.mcp.call_tool_tool import CallToolTool
from languagemodelcommon.mcp.tool_catalog import ToolCatalog
from languagemodelcommon.auth.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from langgraph.store.base import BaseStore
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from languagemodelcommon.utilities.request_information import RequestInformation

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangChainCompletionsProvider(BaseChatCompletionsProvider):
    def __init__(
        self,
        *,
        model_resource_cache_manager: ModelResourceCacheManager,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        mcp_tool_provider: MCPToolProvider,
        token_reader: TokenReader,
        pass_through_token_manager: PassThroughTokenManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        persistence_factory: PersistenceFactory,
        tool_display_name_mapper: ToolDisplayNameMapper,
    ) -> None:
        self.model_resource_cache_manager: ModelResourceCacheManager = (
            model_resource_cache_manager
        )
        if self.model_resource_cache_manager is None:
            raise ValueError("model_resource_cache_manager must not be None")
        if not isinstance(self.model_resource_cache_manager, ModelResourceCacheManager):
            raise TypeError(
                "model_resource_cache_manager must be an instance of ModelResourceCacheManager"
            )
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

        self.tool_display_name_mapper: ToolDisplayNameMapper = tool_display_name_mapper
        if self.tool_display_name_mapper is None:
            raise ValueError("tool_display_name_mapper must not be None")
        if not isinstance(self.tool_display_name_mapper, ToolDisplayNameMapper):
            raise TypeError(
                f"Expected ToolDisplayNameMapper, got {type(self.tool_display_name_mapper)}"
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
        # Retrieve cached model-level resources (LLM, ToolCatalog, base tools)
        cached = self.model_resource_cache_manager.get_or_create(
            model_config=model_config,
        )
        llm = cached.llm

        # noinspection PyUnusedLocal
        def get_current_time(*args: Any, **kwargs: Any) -> str:
            """Returns the current time in H:MM AM/PM format."""
            now = datetime.datetime.now()  # Get current time
            return now.strftime("%Y-%m-%d %H:%M:%S%Z%z")

        # Start with the cached base tools (non-MCP tools from ToolProvider)
        tools: list[BaseTool] = list(cached.base_tools)

        # Create a per-request auth interceptor so concurrent requests
        # don't share mutable auth state
        mcp_tool_configs: list[AgentConfig] = (
            [t for t in model_config.get_agents()]
            if model_config.get_agents() is not None
            else []
        )
        auth_interceptor = AuthMcpCallInterceptor(
            pass_through_token_manager=self.pass_through_token_manager,
            tool_configs=mcp_tool_configs,
            auth_information=auth_information,
            headers=headers,
        )

        # Create a per-request session pool so MCP connections are reused
        # across tool calls within this request
        session_pool = McpSessionPool()
        await session_pool.__aenter__()

        # add MCP tools — either via meta-discovery or direct loading
        tool_catalog: ToolCatalog | None = None
        if model_config.use_tool_discovery:
            # Reuse the cached catalog; only per-request items (resolver, session_pool) are new
            tool_catalog = cached.catalog
            resolver = self.mcp_tool_provider.create_tool_resolver(
                headers=headers,
                auth_interceptor=auth_interceptor,
            )
            tools.append(SearchToolsTool(catalog=tool_catalog, resolver=resolver))
            tools.append(
                CallToolTool(
                    catalog=tool_catalog,
                    mcp_tool_provider=self.mcp_tool_provider,
                    auth_interceptor=auth_interceptor,
                    session_pool=session_pool,
                    proxy_base_url=self.environment_variables.mcp_app_proxy_base_url,
                )
            )
        else:
            tools = tools + await self.mcp_tool_provider.get_tools_async(
                tools=mcp_tool_configs,
                headers=headers,
                auth_interceptor=auth_interceptor,
                session_pool=session_pool,
            )

        # finally read any tools from the Responses API request
        tool_configs_from_request: list[AgentConfig] = chat_request_wrapper.get_tools()
        if tool_configs_from_request:
            if model_config.use_tool_discovery:
                # In discovery mode, add request tools to the catalog too
                catalog = self.mcp_tool_provider.discover_tool_catalog(
                    tools=tool_configs_from_request,
                )
                logger.info(
                    "Added %d request tools to discovery catalog",
                    catalog.tool_count,
                )
            else:
                tools_from_request: Sequence[
                    BaseTool
                ] = await self.mcp_tool_provider.get_tools_async(
                    tools=tool_configs_from_request,
                    headers=headers,
                    auth_interceptor=auth_interceptor,
                    session_pool=session_pool,
                )
                tools = list(tools) + list(tools_from_request)

        # Register MCP display names (title metadata) discovered from tools
        self.tool_display_name_mapper.register_from_tools(tools)

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
                tool_catalog=tool_catalog,
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
                    tool_display_name_mapper=self.tool_display_name_mapper,
                ),
                config=None,
                state=None,
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
                        await session_pool.__aexit__(None, None, None)
                        checkpointer_cm.__exit__(None, None, None)
                        store_cm.__exit__(None, None, None)

                result.body_iterator = streaming_wrapper()
                return result
            else:
                await session_pool.__aexit__(None, None, None)
                checkpointer_cm.__exit__(None, None, None)
                store_cm.__exit__(None, None, None)
                return result
        except Exception as e:
            await session_pool.__aexit__(None, None, None)
            checkpointer_cm.__exit__(type(e), e, e.__traceback__)
            store_cm.__exit__(type(e), e, e.__traceback__)
            raise
