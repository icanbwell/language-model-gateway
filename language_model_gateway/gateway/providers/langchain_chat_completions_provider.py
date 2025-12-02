import datetime
import logging
import uuid
from typing import (
    Dict,
    Any,
    Sequence,
    List,
    AsyncGenerator,
    ContextManager,
    override,
)

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from oidcauthlib.auth.config.auth_config import AuthConfig
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig, AgentConfig
from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.token_reader import TokenReader

from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
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
from language_model_gateway.gateway.tools.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
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
        auth_manager: AuthManager,
        tool_auth_manager: ToolAuthManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        auth_config_reader: AuthConfigReader,
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

        self.auth_manager: AuthManager = auth_manager
        if self.auth_manager is None:
            raise ValueError("auth_manager must not be None")
        if not isinstance(self.auth_manager, AuthManager):
            raise TypeError("auth_manager must be an instance of AuthManager")

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

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )

        self.persistence_factory: PersistenceFactory = persistence_factory
        if self.persistence_factory is None:
            raise ValueError("persistence_factory must not be None")
        if not isinstance(self.persistence_factory, PersistenceFactory):
            raise TypeError(
                "persistence_factory must be an instance of PersistenceFactory"
            )

        self.tool_auth_manager: ToolAuthManager = tool_auth_manager
        if self.tool_auth_manager is None:
            raise ValueError("tool_auth_manager must not be None")
        if not isinstance(self.tool_auth_manager, ToolAuthManager):
            raise TypeError("tool_auth_manager must be an instance of ToolAuthManager")

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

        # finally read any tools from the Responses API request
        tool_configs_from_request: list[AgentConfig] = chat_request_wrapper.get_tools()
        if tool_configs_from_request:
            tools_from_request: Sequence[BaseTool] = (
                self.tool_provider.get_tools(
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
            auth_headers = [
                headers.get(key) for key in headers if key.lower() == "authorization"
            ]
            auth_header: str | None = auth_headers[0] if auth_headers else None
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

        tool_auth_providers: list[str] | None = tool_using_authentication.auth_providers
        if (
            tool_using_authentication.auth_providers is None
            or len(tool_using_authentication.auth_providers) == 0
        ):
            logger.debug(
                f"Tool {tool_using_authentication.name} doesn't have auth providers."
            )
            return
        if not auth_information.redirect_uri:
            logger.debug("AuthInformation doesn't have redirect_uri.")
            return

        tool_first_auth_provider: str | None = (
            tool_auth_providers[0] if tool_auth_providers is not None else None
        )
        auth_config: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=tool_first_auth_provider
            )
            if tool_first_auth_provider is not None
            else None
        )
        if auth_config is None:
            raise ValueError(
                f"AuthConfig not found for auth provider {tool_first_auth_provider}"
                f" used by tool {tool_using_authentication.name}."
            )
        if not auth_information.subject:
            logger.error(
                f"AuthInformation doesn't have subject: {auth_information} in token: {auth_header}"
            )
            raise ValueError(
                "AuthInformation must have subject to authenticate for tools."
                + (f"{auth_information}" if logger.isEnabledFor(logging.DEBUG) else "")
            )
        if not tool_first_auth_provider:
            raise ValueError("Tool using authentication must have an auth provider.")
        tool_client_id: str | None = (
            auth_config.client_id if auth_config is not None else None
        )
        if not tool_client_id:
            raise ValueError("Tool using authentication must have a client ID.")

        authorization_url: str | None = (
            await self.auth_manager.create_authorization_url(
                auth_provider=tool_first_auth_provider,
                redirect_uri=auth_information.redirect_uri,
                url=tool_using_authentication.url,
                referring_email=auth_information.email,
                referring_subject=auth_information.subject,
            )
            if tool_using_authentication is not None
            else None
        )
        error_message: str = (
            f"\nFollowing tools require authentication: {tool_using_authentication.name}."
            + f"\nClick here to [Login to {auth_config.friendly_name}]({authorization_url})."
        )
        # we don't care about the token but just verify it exists so we can throw an error if it doesn't
        await self.tool_auth_manager.get_token_for_tool_async(
            auth_header=auth_header,
            error_message=error_message,
            tool_config=tool_using_authentication,
        )
