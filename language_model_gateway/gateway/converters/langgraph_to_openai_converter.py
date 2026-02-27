import logging
import os
import re
import traceback
from typing import (
    Any,
    List,
    Sequence,
    Optional,
    Tuple,
    Literal,
)
from typing import (
    Dict,
    AsyncGenerator,
    Iterable,
)

import botocore
from botocore.exceptions import TokenRetrievalError
from fastapi import HTTPException
from langchain_community.adapters.openai import (
    convert_message_to_dict,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AnyMessage,
    UsageMetadata,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.schema import CustomStreamEvent, StandardStreamEvent
from langchain_core.tools import BaseTool, ToolException
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.store.base import BaseStore
from openai.types import CompletionUsage
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.gateway.converters.language_model_gateway_exception import (
    LanguageModelGatewayException,
)
from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.converters.streaming_manager import (
    LangGraphStreamingManager,
)
from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangGraphToOpenAIConverter:
    def __init__(
        self,
        *,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        token_reducer: TokenReducer,
        streaming_manager: LangGraphStreamingManager,
        skill_loader: SkillLoaderProtocol,
    ) -> None:
        if environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                f"environment_variables must be EnvironmentVariables, got {type(environment_variables)}"
            )
        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )

        if token_reducer is None:
            raise ValueError("token_reducer must not be None")
        if not isinstance(token_reducer, TokenReducer):
            raise TypeError(
                f"token_reducer must be TokenReducer, got {type(token_reducer)}"
            )
        self.token_reducer = token_reducer

        self.streaming_manager = streaming_manager
        if self.streaming_manager is None:
            raise ValueError("streaming_manager must not be None")
        if not isinstance(self.streaming_manager, LangGraphStreamingManager):
            raise TypeError(
                f"streaming_manager must be LangGraphStreamingManager, got {type(self.streaming_manager)}"
            )

        self.skill_loader = skill_loader
        if self.skill_loader is None:
            raise ValueError("skill_loader must not be None")
        if not isinstance(self.skill_loader, SkillLoaderProtocol):
            raise TypeError(
                f"skill_loader must be SkillLoaderProtocol, got {type(self.skill_loader)}"
            )

    async def _stream_resp_async_generator(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: List[ChatMessageWrapper],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously generate streaming responses from the agent.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            messages: The list of chat completion message parameters.
            request_information: The request information.

        Yields:
            The streaming response as a string.
        """
        request_id = request_information.request_id

        # Track tool start times for concurrent tool runs
        tool_start_times: Dict[str, float] = {}

        try:
            # Process streamed events from the graph and yield messages over the SSE stream.
            event: StandardStreamEvent | CustomStreamEvent
            async for event in self.astream_events(
                chat_request_wrapper=chat_request_wrapper,
                compiled_state_graph=compiled_state_graph,
                messages=messages,
                request_information=request_information,
                config=config,
                state=state,
            ):
                if not event:
                    continue

                async for chunk in self.streaming_manager.handle_langchain_event(
                    event=event,
                    chat_request_wrapper=chat_request_wrapper,
                    request_information=request_information,
                    tool_start_times=tool_start_times,
                ):
                    yield chunk
        except TokenRetrievalError as e:
            message: str = f"Token retrieval error: {e}.  If you are running locally, your AWS session may have expired.  Please re-authenticate using `aws sso login --profile [role]`."
            logger.exception(message)
            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                usage_metadata=None,
                content=message,
                source="error",
            )
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception(f"Exception in _stream_resp_async_generator: {e}\n{tb}")
            # if the request is not enabled for debug logging, return a generic error message instead of the actual error
            error_message: str
            if request_information.enable_debug_logging:
                error_message = f"Error: {e}\n{tb}"
            else:
                error_message = self.environment_variables.generic_error_message

            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                usage_metadata=None,
                content=f"\n{error_message}\n",
                source="error",
            )

        yield chat_request_wrapper.create_final_sse_message(
            request_id=request_id, usage_metadata=None, source="final"
        )

    async def call_agent_with_input(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: List[ChatMessageWrapper],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> StreamingResponse | JSONResponse:
        """
        Call the agent with the provided input and return the response.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will be created using the messages and request information.

        Returns:
            The response as a StreamingResponse or JSONResponse.
        """
        if chat_request_wrapper is None:
            raise ValueError("chat_request must not be None")

        if chat_request_wrapper.stream:
            return StreamingResponse(
                content=await self.get_streaming_response_async(
                    chat_request_wrapper=chat_request_wrapper,
                    compiled_state_graph=compiled_state_graph,
                    system_messages=system_messages,
                    request_information=request_information,
                    config=config,
                    state=state,
                ),
                media_type="text/event-stream",
            )
        else:
            try:
                json_output_requested: bool
                chat_request_wrapper, json_output_requested = (
                    self.add_system_messages_for_json(
                        chat_request_wrapper=chat_request_wrapper
                    )
                )

                chat_request_wrapper = self.add_system_message_for_user_info(
                    chat_request_wrapper=chat_request_wrapper,
                    user_id=request_information.user_id,
                    user_name=request_information.user_name,
                    email=request_information.user_email,
                )

                responses: List[AnyMessage] = await self.ainvoke(
                    compiled_state_graph=compiled_state_graph,
                    chat_request_wrapper=chat_request_wrapper,
                    system_messages=system_messages,
                    request_information=request_information,
                    config=config,
                    state=state,
                )

                content_json: Dict[str, Any] = (
                    chat_request_wrapper.create_non_streaming_response(
                        request_id=request_information.request_id,
                        responses=responses,
                        json_output_requested=json_output_requested,
                    )
                )
                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1" and content_json:
                    logger.info(f"Returning content: {content_json}")

                return JSONResponse(content=content_json)
            except* TokenRetrievalError as e:
                first_exception = e.exceptions[0]
                error_message = (
                    f"AWS Bedrock Token retrieval error: {type(first_exception)} {first_exception}."
                    + "  If you are running locally, your AWS session may have expired."
                    + "  Please re-authenticate using `aws sso login --profile [role]`."
                )
                logger.exception(error_message)
                raise HTTPException(
                    status_code=401,
                    detail=error_message,
                )
            except* botocore.exceptions.NoCredentialsError as e:
                first_exception1 = e.exceptions[0]
                error_message = (
                    f"AWS Bedrock Login error: {type(first_exception1)} {first_exception1}."
                    + "  If you are running locally, your AWS session may have expired."
                    + "  Please re-authenticate using `aws sso login --profile [role]`."
                )
                logger.exception(error_message)
                raise HTTPException(
                    status_code=401,
                    detail=error_message,
                )
            except* Exception as e:
                first_exception2 = e.exceptions[0] if len(e.exceptions) > 0 else e
                # print type of first exception in ExceptionGroup
                # if there is just one exception, we can log it directly
                if len(e.exceptions) > 0:
                    logger.exception(
                        f"ExceptionGroup in call_agent_with_input: {type(first_exception2)} {first_exception2}",
                    )
                # Get the traceback for the first exception
                stack = "".join(
                    traceback.format_exception(
                        type(first_exception2),
                        first_exception2,
                        first_exception2.__traceback__,
                    )
                )
                log_message = f"Unexpected error: {type(first_exception2)} {first_exception2}\nStack trace:\n{stack}"
                logger.exception(log_message)
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error: {first_exception2}",
                )

    @staticmethod
    def add_system_message_for_user_info(
        *,
        chat_request_wrapper: ChatRequestWrapper,
        user_id: Optional[str],
        user_name: Optional[str],
        email: Optional[str],
    ) -> ChatRequestWrapper:
        content: str = (
            f"You are interacting with user_id: {user_id} who is named {user_name} and has email {email}"
            if user_id
            else "You are interacting with an anonymous user"
        )

        new_system_message: ChatMessageWrapper = (
            chat_request_wrapper.create_system_message(content=content)
        )
        chat_request_wrapper.append_message(message=new_system_message)

        return chat_request_wrapper

    @staticmethod
    def add_system_messages_for_json(
        *, chat_request_wrapper: ChatRequestWrapper
    ) -> Tuple[ChatRequestWrapper, bool]:
        """
        If the user is requesting json_object or json_schema output, add system messages to the chat request
        to generate JSON output.


        :param chat_request_wrapper:
        :return:
        """
        json_response_requested: bool = False
        response_format: Literal["text", "json_object", "json_schema"] | None = (
            chat_request_wrapper.response_format
        )
        if not response_format:
            return chat_request_wrapper, json_response_requested

        match response_format:
            case "text":
                return chat_request_wrapper, json_response_requested
            case "json_object":
                json_response_requested = True
                json_object_system_message_text: str = """
                Respond only with a JSON object or array.

                Output follows this example format:
                <json>
                json  here
                </json>"""
                json_object_system_message: ChatMessageWrapper = (
                    chat_request_wrapper.create_system_message(
                        content=json_object_system_message_text
                    )
                )
                chat_request_wrapper.append_message(message=json_object_system_message)
                return chat_request_wrapper, json_response_requested
            case "json_schema":
                json_response_requested = True
                json_schema: str | None = chat_request_wrapper.response_json_schema
                if json_schema is None:
                    raise ValueError(
                        "json_schema should be specified in response_format if type is json_schema"
                    )
                json_schema_system_message_text: str = f"""
                Respond only with a JSON object or array using the provided schema:
                ```{json_schema}```

                Output follows this example format:
                <json>
                json  here
                </json>"""
                json_schema_system_message: ChatMessageWrapper = (
                    chat_request_wrapper.create_system_message(
                        content=json_schema_system_message_text
                    )
                )
                chat_request_wrapper.append_message(message=json_schema_system_message)
                return chat_request_wrapper, json_response_requested
            case _:
                raise ValueError(f"Unexpected response format type: {response_format}")

    async def get_streaming_response_async(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: List[ChatMessageWrapper],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> AsyncGenerator[str, None]:
        """
        Get the streaming response asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will be created using the messages and request information.

        Returns:
            The streaming response as an async generator.
        """

        new_messages: List[ChatMessageWrapper] = [
            m for m in chat_request_wrapper.messages
        ]
        messages: List[ChatMessageWrapper] = [s for s in system_messages] + new_messages

        logger.debug(f"Streaming response {request_information.request_id} from agent")
        generator: AsyncGenerator[str, None] = self._stream_resp_async_generator(
            chat_request_wrapper=chat_request_wrapper,
            compiled_state_graph=compiled_state_graph,
            messages=messages,
            request_information=request_information,
            config=config,
            state=state,
        )
        return generator

    # noinspection PyMethodMayBeStatic
    async def _run_graph_with_messages_async(
        self,
        *,
        messages: List[AnyMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> List[AnyMessage]:
        """
        Run the graph with the provided messages asynchronously.

        Args:
            messages: The list of role and incoming message type tuples.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will be created using the messages and request information.

        Returns:
            The list of any messages.
        """

        input_: MyMessagesState = state or self.create_state(
            messages=messages,
            request_information=request_information,
        )
        config = config or {
            "configurable": {
                "thread_id": request_information.conversation_thread_id,
                "user_id": request_information.user_id,
            }
        }
        try:
            output: Dict[str, Any] = await compiled_state_graph.ainvoke(
                input=input_, config=config
            )
        except AttributeError as e:
            # Fallback if errorfactory is not available
            logger.exception(f"AttributeError in throttling handling: {e}")
            raise
        except Exception as e:
            # Try to catch ThrottlingException dynamically
            if (
                hasattr(e, "__class__")
                and e.__class__.__name__ == "ThrottlingException"
            ):
                logger.exception(f"AWS ThrottlingException: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="AWS request throttled. Please try again later.",
                )
            raise
        out_messages: List[AnyMessage] = output["messages"]
        return out_messages

    # noinspection PyMethodMayBeStatic
    async def _stream_graph_with_messages_async(
        self,
        *,
        messages: List[AnyMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream the graph with the provided messages asynchronously.

        Args:
            messages: The list of role and incoming message type tuples.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will

        Yields:
            The standard or custom stream event.
        """

        config = config or {
            "configurable": {
                "thread_id": request_information.conversation_thread_id,
                "user_id": request_information.user_id,
            }
        }
        try:
            event: StandardStreamEvent | CustomStreamEvent
            async for event in compiled_state_graph.astream_events(
                input=state
                or self.create_state(
                    messages=messages,
                    request_information=request_information,
                ),
                version="v2",
                config=config,
            ):
                yield event
        except ToolException as e:
            messages_dict: List[dict[str, Any]] = [
                convert_message_to_dict(m) for m in messages
            ]
            logger.exception(
                "ToolException occurred: {}. Messages: {}",
                e,
                messages_dict,
            )
            raise LanguageModelGatewayException(
                f"Tool Error streaming graph with messages: {e}"
            ) from e
        except Exception as e:
            messages_dict = [convert_message_to_dict(m) for m in messages]
            logger.exception(
                "Exception occurred while streaming graph with messages: {}. Messages: {}",
                e,
                messages_dict,
            )
            raise LanguageModelGatewayException(
                f"Error streaming graph with messages: {e}"
            ) from e

    # noinspection SpellCheckingInspection
    async def ainvoke(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: Iterable[ChatMessageWrapper],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> List[AnyMessage]:
        """
        Run the agent asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The iterable of chat completion message parameters.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will be created using the messages and request information.

        Returns:
            The list of any messages.
        """
        if chat_request_wrapper is None:
            raise ValueError("request must not be None")

        new_messages: List[ChatMessageWrapper] = [
            m for m in chat_request_wrapper.messages
        ]
        messages: List[ChatMessageWrapper] = [s for s in system_messages] + new_messages

        return await self._run_graph_with_messages_async(
            compiled_state_graph=compiled_state_graph,
            messages=self.create_messages_for_graph(messages=messages),
            request_information=request_information,
            config=config,
            state=state,
        )

    async def astream_events(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: Iterable[ChatMessageWrapper],
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream events asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            messages: The iterable of chat completion message parameters.
            request_information: The request information.
            config: Optional configuration for the runnable execution.
            state: Optional state to run the graph with. If not provided, a new state will

        Yields:
            The standard or custom stream event.
        """
        event: StandardStreamEvent | CustomStreamEvent
        async for event in self._stream_graph_with_messages_async(
            compiled_state_graph=compiled_state_graph,
            messages=self.create_messages_for_graph(messages=messages),
            request_information=request_information,
            config=config,
            state=state,
        ):
            yield event

    # noinspection PyMethodMayBeStatic
    def create_messages_for_graph(
        self, *, messages: Iterable[ChatMessageWrapper]
    ) -> List[AnyMessage]:
        """
        Create messages for the graph.

        Args:
            messages: The iterable of chat completion message parameters.

        Returns:
            The list of role and incoming message type tuples.
        """

        messages_: List[AnyMessage] = [m.to_langchain_message() for m in messages]
        return messages_

    async def run_graph_async(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
        config: RunnableConfig | None,
        state: Optional[MyMessagesState],
    ) -> List[AnyMessage]:
        """
        Run the graph asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.
            config: RunnableConfig | None
            state: Optional state to run the graph with. If not provided, a new state will be created.

        Returns:
            The list of any messages.
        """
        messages: List[AnyMessage] = self.create_messages_for_graph(
            messages=chat_request_wrapper.messages
        )

        output_messages: List[AnyMessage] = await self._run_graph_with_messages_async(
            compiled_state_graph=compiled_state_graph,
            messages=messages,
            request_information=request_information,
            config=config,
            state=state,
        )
        return output_messages

    # noinspection PyMethodMayBeStatic
    async def create_graph_for_llm_async(
        self,
        *,
        llm: BaseChatModel,
        tools: Sequence[BaseTool],
        store: BaseStore | None,
        checkpointer: BaseCheckpointSaver[str] | None,
        enable_health_safety: bool | None = None,
        system_prompts: List[str] | None = None,
    ) -> CompiledStateGraph[MyMessagesState]:
        """
        Create a graph for the language model asynchronously.

        Optionally includes a health safety evaluation node that can evaluate
        and refine AI responses before they are returned to the user.

        Args:
            llm: The language model to use
            tools: List of tools available to the agent
            store: Optional store for persistence
            checkpointer: Optional checkpointer for state management
            enable_health_safety: Whether to enable health safety evaluation.
                                  If None, reads from HEALTH_SAFETY_ENABLE_EVALUATOR env var.
            system_prompts: Optional list of system prompts to prepend to the agent
        """
        tool_node: Optional[ToolNode] = None

        if len(tools) > 0:
            tool_node = StreamingToolNode(tools)

        # https://langchain-ai.github.io/langgraph/concepts/persistence/
        compiled_state_graph: CompiledStateGraph[MyMessagesState] = create_react_agent(
            model=llm,
            tools=tool_node if tool_node is not None else [],
            state_schema=MyMessagesState,
            store=store,
            checkpointer=checkpointer,
        )
        return compiled_state_graph

    @staticmethod
    def create_state(
        *,
        messages: List[AnyMessage],
        request_information: RequestInformation,
    ) -> MyMessagesState:
        """
        Create the state.
        """

        input1: MyMessagesState = MyMessagesState(
            messages=messages,
            auth_token=LangGraphToOpenAIConverter.get_auth_token_from_headers(
                headers=request_information.headers
            ),
            usage_metadata=None,
            user_id=request_information.user_id,
            conversation_thread_id=request_information.conversation_thread_id,
            passed_evaluation=None,
            evaluation_notes=None,
        )
        return input1

    @staticmethod
    def get_auth_token_from_headers(headers: Dict[str, str]) -> Optional[str]:
        """
        Get the auth token from the headers.

        Args:
            headers: The headers.

        Returns:
            The auth token.
        """
        # Normalize headers to handle case-insensitive matching
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Check for authorization header variations
        auth_headers = ["authorization"]

        for header_key in auth_headers:
            header_value = normalized_headers.get(header_key.lower())

            if header_value:
                # Use regex to extract bearer token
                match = re.search(r"Bearer\s+(\S+)", str(header_value), re.IGNORECASE)
                if match:
                    return match.group(1)

        return None

    # noinspection PyMethodMayBeStatic
    def convert_usage_meta_data_to_openai(
        self, *, usages: List[UsageMetadata]
    ) -> CompletionUsage:
        total_usage_metadata: CompletionUsage = CompletionUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
        usage_metadata: UsageMetadata
        for usage_metadata in usages:
            total_usage_metadata.prompt_tokens += usage_metadata["input_tokens"]
            total_usage_metadata.completion_tokens += usage_metadata["output_tokens"]
            total_usage_metadata.total_tokens += usage_metadata["total_tokens"]
        return total_usage_metadata
