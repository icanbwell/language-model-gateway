import datetime
import logging
import random
from typing import Dict, Any, Sequence, List, AsyncGenerator

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig, AgentConfig
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.models.auth import AuthInformation
from language_model_gateway.gateway.auth.token_reader import TokenReader
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
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.tools.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)
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
        auth_manager: AuthManager,
        environment_variables: EnvironmentVariables,
        auth_config_reader: AuthConfigReader,
        persistence_factory: PersistenceFactory,
    ) -> None:
        self.model_factory: ModelFactory = model_factory
        assert self.model_factory is not None
        assert isinstance(self.model_factory, ModelFactory)
        self.lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter = (
            lang_graph_to_open_ai_converter
        )
        assert self.lang_graph_to_open_ai_converter is not None
        assert isinstance(
            self.lang_graph_to_open_ai_converter, LangGraphToOpenAIConverter
        )
        self.tool_provider: ToolProvider = tool_provider
        assert self.tool_provider is not None
        assert isinstance(self.tool_provider, ToolProvider)

        self.mcp_tool_provider: MCPToolProvider = mcp_tool_provider
        assert self.mcp_tool_provider is not None
        assert isinstance(self.mcp_tool_provider, MCPToolProvider)

        self.token_reader: TokenReader = token_reader
        assert self.token_reader is not None
        assert isinstance(self.token_reader, TokenReader)

        self.auth_manager: AuthManager = auth_manager
        assert self.auth_manager is not None
        assert isinstance(self.auth_manager, AuthManager)

        self.environment_variables: EnvironmentVariables = environment_variables
        assert self.environment_variables is not None
        assert isinstance(self.environment_variables, EnvironmentVariables)

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        assert self.auth_config_reader is not None
        assert isinstance(self.auth_config_reader, AuthConfigReader)

        self.persistence_factory: PersistenceFactory = persistence_factory
        assert self.persistence_factory is not None
        assert isinstance(self.persistence_factory, PersistenceFactory)

    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request: ChatRequest,
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
        await self.check_tokens_are_valid_for_tools(
            auth_information=auth_information,
            headers=headers,
            model_config=model_config,
        )

        # add MCP tools
        tools = [t for t in tools] + await self.mcp_tool_provider.get_tools_async(
            tools=[t for t in model_config.get_agents()],
            headers=headers,
        )

        # Use context managers only for the duration of streaming
        store_cm = self.persistence_factory.create_store(
            persistence_type=self.environment_variables.llm_storage_type,
        )
        checkpointer_cm = self.persistence_factory.create_checkpointer(
            persistence_type=self.environment_variables.llm_storage_type,
        )
        try:
            store = store_cm.__enter__()
            checkpointer = checkpointer_cm.__enter__()
            compiled_state_graph: CompiledStateGraph[
                MyMessagesState
            ] = await self.lang_graph_to_open_ai_converter.create_graph_for_llm_async(
                llm=llm,
                tools=tools,
                store=store,
                checkpointer=checkpointer,
            )
            request_id = random.randint(1, 1000)

            conversation_thread_id: str | None = headers.get("X-Chat-Id".lower())

            result = await self.lang_graph_to_open_ai_converter.call_agent_with_input(
                compiled_state_graph=compiled_state_graph,
                chat_request=chat_request,
                system_messages=[],
                request_information=RequestInformation(
                    auth_information=auth_information,
                    user_id=auth_information.subject,
                    user_email=auth_information.email,
                    user_name=auth_information.user_name,
                    request_id=str(request_id),
                    conversation_thread_id=conversation_thread_id or str(request_id),
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

    async def check_tokens_are_valid_for_tools(
        self,
        *,
        auth_information: AuthInformation,
        headers: Dict[str, Any],
        model_config: ChatModelConfig,
    ) -> None:
        # check if any of the MCP tools require authentication
        tools_using_authentication: List[AgentConfig] = [
            a for a in model_config.get_agents() if a.auth == "jwt_token"
        ]
        if any(tools_using_authentication):
            # check that we have a valid Authorization header
            auth_header: str | None = next(
                (headers.get(key) for key in headers if key.lower() == "authorization"),
                None,
            )
            tool_using_authentication: AgentConfig
            for tool_using_authentication in tools_using_authentication:
                await self.check_tokens_are_valid_for_tool(
                    auth_header=auth_header,
                    auth_information=auth_information,
                    tool_using_authentication=tool_using_authentication,
                )
        else:
            logger.debug("No tools require authentication.")

    async def check_tokens_are_valid_for_tool(
        self,
        *,
        auth_header: str | None,
        auth_information: AuthInformation,
        tool_using_authentication: AgentConfig,
    ) -> None:
        """
        Check if the provided token is valid for the specified tool.
        Args:
            auth_header (str | None): The Authorization header containing the token.
            auth_information (AuthInformation): The authentication information.
            tool_using_authentication (AgentConfig): The tool configuration requiring authentication.
        """
        if not tool_using_authentication.auth_providers:
            logger.debug(
                f"Tool {tool_using_authentication.name} doesn't have auth providers."
            )
            return
        if not auth_information.redirect_uri:
            logger.debug("AuthInformation doesn't have redirect_uri.")
            return

        tool_first_auth_provider: str = tool_using_authentication.auth_providers[0]
        tool_first_issuer: str | None = (
            tool_using_authentication.issuers[0]
            if tool_using_authentication.issuers
            else self.auth_config_reader.get_issuer_for_provider(
                auth_provider=tool_first_auth_provider,
            )
        )
        assert tool_first_issuer, (
            "Tool using authentication must have at least one issuer or use the default issuer."
        )
        tool_first_audience: str = self.auth_config_reader.get_audience_for_provider(
            auth_provider=tool_first_auth_provider
        )
        if not auth_information.email:
            raise ValueError(
                "AuthInformation must have email to authenticate for tools."
            )
        if not auth_information.subject:
            raise ValueError(
                "AuthInformation must have subject to authenticate for tools."
            )
        authorization_url: str | None = (
            await self.auth_manager.create_authorization_url(
                audience=tool_first_audience,  # use the first audience to get a new authorization URL
                redirect_uri=auth_information.redirect_uri,
                issuer=tool_first_issuer,
                url=tool_using_authentication.url,
                referring_email=auth_information.email,
                referring_subject=auth_information.subject,
            )
            if tool_using_authentication
            else None
        )
        error_message: str = (
            f"\nFollowing tools require authentication: {tool_using_authentication.name}."
            + f"\nClick here to authenticate: [Login to {tool_first_auth_provider}]({authorization_url})."
        )
        # we don't care about the token but just verify it exists so we can throw an error if it doesn't
        await self.auth_manager.get_token_for_tool_async(
            auth_header=auth_header,
            error_message=error_message,
            tool_name=tool_using_authentication.name,
            tool_auth_providers=tool_using_authentication.auth_providers,
        )
