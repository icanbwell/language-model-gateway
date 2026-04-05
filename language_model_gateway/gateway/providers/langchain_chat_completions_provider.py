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

from langchain_ai_skills_framework.loaders.skill_loader_protocol import (
    SkillLoaderProtocol,
)
from langchain_ai_skills_framework.tools.run_python_script_tool import (
    RunPythonScriptTool,
)
from languagemodelcommon.utilities.tool_display_name_mapper import (
    ToolDisplayNameMapper,
)
from starlette.responses import StreamingResponse, JSONResponse

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from languagemodelcommon.configs.schemas.config_schema import (
    ChatModelConfig,
    AgentConfig,
)
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.token_reader import TokenReader

from languagemodelcommon.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from languagemodelcommon.state.messages_state import MyMessagesState
from language_model_gateway.gateway.models.model_factory import ModelFactory
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
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider
from languagemodelcommon.mcp.search_tools_tool import SearchToolsTool
from languagemodelcommon.mcp.call_tool_tool import CallToolTool
from languagemodelcommon.mcp.tool_catalog import ToolCatalog
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
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
        model_factory: ModelFactory,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
        token_reader: TokenReader,
        pass_through_token_manager: PassThroughTokenManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        persistence_factory: PersistenceFactory,
        skill_loader: SkillLoaderProtocol,
        tool_display_name_mapper: ToolDisplayNameMapper,
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

        self.skill_loader: SkillLoaderProtocol = skill_loader
        if self.skill_loader is None:
            raise ValueError("skill_loader must not be None")
        if not isinstance(self.skill_loader, SkillLoaderProtocol):
            raise TypeError(
                f"skill_loader must be an instance of SkillLoaderProtocol: {type(self.skill_loader)}"
            )

        self.tool_display_name_mapper: ToolDisplayNameMapper = tool_display_name_mapper
        if self.tool_display_name_mapper is None:
            raise ValueError("tool_display_name_mapper must not be None")
        if not isinstance(self.tool_display_name_mapper, ToolDisplayNameMapper):
            raise TypeError(
                f"Expected ToolDisplayNameMapper, got {type(self.tool_display_name_mapper)}"
            )

    def _add_discovery_tools(
        self,
        *,
        tools: list[BaseTool],
        mcp_tool_configs: list[AgentConfig],
        headers: Dict[str, str],
        auth_interceptor: AuthMcpCallInterceptor,
    ) -> tuple[list[BaseTool], ToolCatalog | None]:
        """Replace direct MCP tool loading with meta-discovery tools.

        Builds a ToolCatalog from MCP servers and adds search_tools +
        call_tool to the tool list. The ToolDiscoveryMiddleware is
        responsible for injecting category descriptions into the system
        prompt at model-call time.

        Returns:
            A tuple of (tools, catalog). The catalog is ``None`` when no
            categories were registered.
        """
        catalog = self.mcp_tool_provider.discover_tool_catalog(
            tools=mcp_tool_configs,
        )

        categories = catalog.get_categories()
        if categories:
            resolver = self.mcp_tool_provider.create_tool_resolver(
                headers=headers,
                auth_interceptor=auth_interceptor,
            )
            tools.append(
                SearchToolsTool(catalog=catalog, resolver=resolver)
            )
            tools.append(
                CallToolTool(
                    catalog=catalog,
                    mcp_tool_provider=self.mcp_tool_provider,
                    auth_interceptor=auth_interceptor,
                )
            )
            logger.info(
                "Tool discovery enabled: %d categories registered",
                len(categories),
            )
            return tools, catalog

        logger.warning("Tool discovery enabled but no tools found in catalog")
        return tools, None

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

        # add MCP tools — either via meta-discovery or direct loading
        tool_catalog: ToolCatalog | None = None
        if model_config.use_tool_discovery:
            tools, tool_catalog = self._add_discovery_tools(
                tools=list(tools),
                mcp_tool_configs=mcp_tool_configs,
                headers=headers,
                auth_interceptor=auth_interceptor,
            )
        else:
            tools = [t for t in tools] + await self.mcp_tool_provider.get_tools_async(
                tools=mcp_tool_configs,
                headers=headers,
                auth_interceptor=auth_interceptor,
            )

        # add the skills tools
        tools += self.skill_loader.get_tools()

        if self.environment_variables.enable_code_interpreter:
            tools += [RunPythonScriptTool()]

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
                )
                tools = list(tools) + list(tools_from_request)

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
                skill_loader=self.skill_loader,
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
