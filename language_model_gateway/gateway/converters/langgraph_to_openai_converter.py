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
    BaseMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.schema import CustomStreamEvent, StandardStreamEvent
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.store.base import BaseStore
from starlette.responses import StreamingResponse, JSONResponse

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
from language_model_gateway.gateway.converters.streaming_utils import (
    format_done_sse,
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
    ) -> None:
        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                f"environment_variables must be EnvironmentVariables, got {type(self.environment_variables)}"
            )
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        self.token_reducer = token_reducer
        if self.token_reducer is None:
            raise ValueError("token_reducer must not be None")
        if not isinstance(self.token_reducer, TokenReducer):
            raise TypeError(
                f"token_reducer must be TokenReducer, got {type(self.token_reducer)}"
            )
        self.streaming_manager = streaming_manager
        if self.streaming_manager is None:
            raise ValueError("streaming_manager must not be None")
        if not isinstance(self.streaming_manager, LangGraphStreamingManager):
            raise TypeError(
                f"streaming_manager must be LangGraphStreamingManager, got {type(self.streaming_manager)}"
            )

    async def _stream_resp_async_generator(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: List[ChatMessageWrapper],
        request_information: RequestInformation,
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
            ):
                if not event:
                    continue

                async for chunk in self.streaming_manager.handle_langchain_event(
                    event=event,
                    chat_request_wrapper=chat_request_wrapper,
                    request_id=request_id,
                    tool_start_times=tool_start_times,
                ):
                    yield chunk
        except TokenRetrievalError as e:
            logger.exception(e, stack_info=True)
            message: str = f"Token retrieval error: {e}.  If you are running locally, your AWS session may have expired.  Please re-authenticate using `aws sso login --profile [role]`."
            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                usage_metadata=None,
                content=message,
            )
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(
                f"Exception in _stream_resp_async_generator: {e}\n{tb}", exc_info=True
            )
            error_message = f"Error: {e}\nTraceback:\n{tb}"
            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                usage_metadata=None,
                content=f"\n{error_message}\n",
            )

        yield chat_request_wrapper.create_final_sse_message(
            request_id=request_id, usage_metadata=None
        )

        yield format_done_sse()

    async def call_agent_with_input(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: List[ChatMessageWrapper],
        request_information: RequestInformation,
    ) -> StreamingResponse | JSONResponse:
        """
        Call the agent with the provided input and return the response.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.

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
                logger.exception(e, stack_info=True)
                first_exception = e.exceptions[0]
                raise HTTPException(
                    status_code=401,
                    detail=f"AWS Bedrock Token retrieval error: {type(first_exception)} {first_exception}."
                    + "  If you are running locally, your AWS session may have expired."
                    + "  Please re-authenticate using `aws sso login --profile [role]`.",
                )
            except* botocore.exceptions.NoCredentialsError as e:
                logger.exception(e, stack_info=True)
                first_exception1 = e.exceptions[0]
                raise HTTPException(
                    status_code=401,
                    detail=f"AWS Bedrock Login error: {type(first_exception1)} {first_exception1}."
                    + "  If you are running locally, your AWS session may have expired."
                    + "  Please re-authenticate using `aws sso login --profile [role]`.",
                )
            except* Exception as e:
                logger.exception(e, stack_info=True)
                first_exception2 = e.exceptions[0] if len(e.exceptions) > 0 else e
                # print type of first exception in ExceptionGroup
                # if there is just one exception, we can log it directly
                if len(e.exceptions) > 0:
                    logger.error(
                        f"ExceptionGroup in call_agent_with_input: {type(first_exception2)} {first_exception2}",
                        exc_info=True,
                    )
                # Get the traceback for the first exception
                stack = "".join(
                    traceback.format_exception(
                        type(first_exception2),
                        first_exception2,
                        first_exception2.__traceback__,
                    )
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error: {type(first_exception2)} {first_exception2}\nStack trace:\n{stack}",
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
    ) -> AsyncGenerator[str, None]:
        """
        Get the streaming response asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.

        Returns:
            The streaming response as an async generator.
        """

        new_messages: List[ChatMessageWrapper] = [
            m for m in chat_request_wrapper.messages
        ]
        messages: List[ChatMessageWrapper] = [s for s in system_messages] + new_messages

        logger.info(f"Streaming response {request_information.request_id} from agent")
        generator: AsyncGenerator[str, None] = self._stream_resp_async_generator(
            chat_request_wrapper=chat_request_wrapper,
            compiled_state_graph=compiled_state_graph,
            messages=messages,
            request_information=request_information,
        )
        return generator

    # noinspection PyMethodMayBeStatic
    async def _run_graph_with_messages_async(
        self,
        *,
        messages: List[BaseMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the graph with the provided messages asynchronously.

        Args:
            messages: The list of role and incoming message type tuples.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.

        Returns:
            The list of any messages.
        """

        input_: MyMessagesState = self.create_state(
            messages=messages,
            request_information=request_information,
        )
        config: RunnableConfig = {
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
            logger.error(f"AttributeError in throttling handling: {e}")
            raise
        except Exception as e:
            # Try to catch ThrottlingException dynamically
            if (
                hasattr(e, "__class__")
                and e.__class__.__name__ == "ThrottlingException"
            ):
                logger.error(f"AWS ThrottlingException: {e}")
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
        messages: List[BaseMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream the graph with the provided messages asynchronously.

        Args:
            messages: The list of role and incoming message type tuples.
            compiled_state_graph: The compiled state graph.

        Yields:
            The standard or custom stream event.
        """

        config: RunnableConfig = {
            "configurable": {
                "thread_id": request_information.conversation_thread_id,
                "user_id": request_information.user_id,
            }
        }
        try:
            event: StandardStreamEvent | CustomStreamEvent
            async for event in compiled_state_graph.astream_events(
                input=self.create_state(
                    messages=messages,
                    request_information=request_information,
                ),
                version="v2",
                config=config,
            ):
                yield event
        except Exception as e:
            messages_dict: List[dict[str, Any]] = [
                convert_message_to_dict(m) for m in messages
            ]
            logger.exception(
                f"Exception occurred: {e}. Messages: {messages_dict}", stack_info=True
            )
            raise

    # noinspection SpellCheckingInspection
    async def ainvoke(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: Iterable[ChatMessageWrapper],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the agent asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The iterable of chat completion message parameters.
            request_information: The request information.

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
        )

    async def astream_events(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: Iterable[ChatMessageWrapper],
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream events asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            messages: The iterable of chat completion message parameters.
            request_information: The request information.

        Yields:
            The standard or custom stream event.
        """
        event: StandardStreamEvent | CustomStreamEvent
        async for event in self._stream_graph_with_messages_async(
            compiled_state_graph=compiled_state_graph,
            messages=self.create_messages_for_graph(messages=messages),
            request_information=request_information,
        ):
            yield event

    # noinspection PyMethodMayBeStatic
    def create_messages_for_graph(
        self, *, messages: Iterable[ChatMessageWrapper]
    ) -> List[BaseMessage]:
        """
        Create messages for the graph.

        Args:
            messages: The iterable of chat completion message parameters.

        Returns:
            The list of role and incoming message type tuples.
        """

        messages_: List[BaseMessage] = [
            m.to_langchain_message_for_response() for m in messages
        ]
        return messages_

    async def run_graph_async(
        self,
        *,
        chat_request_wrapper: ChatRequestWrapper,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the graph asynchronously.

        Args:
            chat_request_wrapper: The chat request.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.

        Returns:
            The list of any messages.
        """
        messages: List[BaseMessage] = self.create_messages_for_graph(
            messages=chat_request_wrapper.messages
        )

        output_messages: List[AnyMessage] = await self._run_graph_with_messages_async(
            compiled_state_graph=compiled_state_graph,
            messages=messages,
            request_information=request_information,
        )
        return output_messages

    @staticmethod
    async def create_graph_for_llm_async(
        *,
        llm: BaseChatModel,
        tools: Sequence[BaseTool],
        store: BaseStore | None,
        checkpointer: BaseCheckpointSaver[str] | None,
    ) -> CompiledStateGraph[MyMessagesState]:
        """
        Create a graph for the language model asynchronously.

        Args:
            llm: The base chat model.
            tools: The sequence of tools.
            store: The base store for persistence.
            checkpointer: The checkpoint saver for saving state.

        Returns:
            The compiled state graph.
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
        messages: List[BaseMessage],
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
            remaining_steps=0,
            user_id=request_information.user_id,
            conversation_thread_id=request_information.conversation_thread_id,
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
