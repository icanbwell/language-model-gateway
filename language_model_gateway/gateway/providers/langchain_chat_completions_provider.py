import datetime
import random
from typing import Dict, Any, Sequence, List

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig, AgentConfig
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.auth import AuthInformation
from language_model_gateway.gateway.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.tools.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.auth.token_reader import TokenReader


class LangChainCompletionsProvider(BaseChatCompletionsProvider):
    def __init__(
        self,
        *,
        model_factory: ModelFactory,
        lang_graph_to_open_ai_converter: LangGraphToOpenAIConverter,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
        token_verifier: TokenReader,
        auth_manager: AuthManager,
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

        self.token_verifier: TokenReader = token_verifier
        assert self.token_verifier is not None
        assert isinstance(self.token_verifier, TokenReader)

        self.auth_manager: AuthManager = auth_manager
        assert self.auth_manager is not None
        assert isinstance(self.auth_manager, AuthManager)

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

        compiled_state_graph: CompiledStateGraph[
            MyMessagesState
        ] = await self.lang_graph_to_open_ai_converter.create_graph_for_llm_async(
            llm=llm,
            tools=tools,
        )
        request_id = random.randint(1, 1000)

        return await self.lang_graph_to_open_ai_converter.call_agent_with_input(
            request_id=str(request_id),
            headers=headers,
            compiled_state_graph=compiled_state_graph,
            chat_request=chat_request,
            system_messages=[],
        )

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
        if (
            not tool_using_authentication.auth_audience
            or not auth_information.redirect_uri
        ):
            return

        authorization_url: str | None = (
            await self.auth_manager.create_authorization_url(
                audience=tool_using_authentication.auth_audience,
                redirect_uri=auth_information.redirect_uri,
            )
            if tool_using_authentication
            else None
        )
        if not auth_header:
            raise AuthorizationNeededException(
                "Authorization header is required for MCP tools with JWT authentication."
                + f"Following tools require authentication: {tool_using_authentication}"
                + f"Please visit {authorization_url} to authenticate."
            )
        else:
            token: str | None = self.token_verifier.extract_token(auth_header)
            if not token:
                raise AuthorizationNeededException(
                    "Invalid Authorization header format. Expected 'Bearer <token>'"
                    + f"Following tools require authentication: {tool_using_authentication}"
                    + f"Please visit {authorization_url} to authenticate."
                )
            # verify the token
            try:
                token_claims: Dict[
                    str, Any
                ] = await self.token_verifier.verify_token_async(token=token)
                if not token_claims:
                    raise AuthorizationNeededException(
                        "Invalid or expired token provided in Authorization header"
                        + f"Following tools require authentication: {tool_using_authentication}"
                        + f"Please visit {authorization_url} to authenticate."
                    )
                else:
                    token_audience: str | None = token_claims.get("aud")
                    if token_audience != tool_using_authentication.auth_audience:
                        raise AuthorizationNeededException(
                            "Token provided in Authorization header has wrong audience:"
                            + f"Found: {token_audience}, Expected: {tool_using_authentication.auth_audience}"
                            + " and we could not find a cached token for the tool."
                            + f"Following tools require authentication: {tool_using_authentication}"
                            + f"Please visit {authorization_url} to authenticate."
                        )
            except Exception as e:
                raise AuthorizationNeededException(
                    "Invalid or expired token provided in Authorization header."
                    + f" Following tools require authentication: {tool_using_authentication}"
                    + f" Please visit {authorization_url} to authenticate."
                ) from e
