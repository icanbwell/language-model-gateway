import json
import logging
import os
import re
import time
import traceback
from typing import (
    Any,
    List,
    Sequence,
    cast,
    Optional,
    Tuple,
)
from typing import (
    Dict,
    AsyncGenerator,
    Iterable,
)

import botocore
from botocore.exceptions import TokenRetrievalError
from fastapi import HTTPException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.messages import AIMessageChunk
from langchain_core.messages.ai import UsageMetadata
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.schema import CustomStreamEvent, StandardStreamEvent
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.store.base import BaseStore
from openai import NotGiven
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletion,
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice
from openai.types.chat.completion_create_params import ResponseFormat
from openai.types.shared_params import ResponseFormatJSONSchema
from openai.types.shared_params.response_format_json_schema import JSONSchema
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.gateway.converters.my_messages_state import MyMessagesState
from language_model_gateway.gateway.converters.streaming_tool_node import (
    StreamingToolNode,
)
from language_model_gateway.gateway.structures.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.utilities.chat_message_helpers import (
    langchain_to_chat_message,
    convert_message_content_to_string,
)
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)
from language_model_gateway.gateway.utilities.json_extractor import JsonExtractor
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
        environment_variables: EnvironmentVariables,
        token_reducer: TokenReducer,
    ) -> None:
        self.environment_variables: EnvironmentVariables = environment_variables
        if not isinstance(self.environment_variables, EnvironmentVariables):
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

                event_type: str = event["event"]

                # events are described here: https://python.langchain.com/docs/how_to/streaming/#using-stream-events

                # print(f"===== {event_type} =====\n{event}\n")

                event_object = cast(object, event)
                match event_type:
                    case "on_chain_start":
                        # Handle the start of the chain event
                        pass
                    case "on_chain_stream":
                        # Handle the chain stream event.  Be sure not to write duplicate responses to what is done in the on_chat_model_stream event.
                        pass
                    case "on_chat_model_stream":
                        # Handle the chat model stream event
                        event_dict = cast(dict[str, Any], event_object)
                        chunk: AIMessageChunk | None = event_dict.get("data", {}).get(
                            "chunk"
                        )
                        if chunk is not None:
                            content: str | list[str | dict[str, Any]] = chunk.content

                            # print(f"chunk: {chunk}")

                            usage_metadata = chunk.usage_metadata
                            completion_usage_metadata = (
                                self.convert_usage_meta_data_to_openai(
                                    usages=[usage_metadata] if usage_metadata else []
                                )
                            )

                            content_text: str = convert_message_content_to_string(
                                content
                            )
                            if not isinstance(content_text, str):
                                raise TypeError(
                                    f"content_text must be str, got {type(content_text)}"
                                )

                            if (
                                os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1"
                                and content_text
                            ):
                                logger.debug(f"Returning content: {content_text}")

                            if content_text:
                                chat_model_stream_response: ChatCompletionChunk = (
                                    ChatCompletionChunk(
                                        id=request_id,
                                        created=int(time.time()),
                                        model=chat_request_wrapper.model,
                                        choices=[
                                            ChunkChoice(
                                                index=0,
                                                delta=ChoiceDelta(
                                                    role="assistant",
                                                    content=content_text,
                                                ),
                                            )
                                        ],
                                        usage=completion_usage_metadata,
                                        object="chat.completion.chunk",
                                    )
                                )
                                yield f"data: {json.dumps(chat_model_stream_response.model_dump())}\n\n"
                    case "on_chain_end":
                        # print(f"===== {event_type} =====\n{event}\n")
                        event_dict = cast(dict[str, Any], event_object)
                        output: Dict[str, Any] | str | None = event_dict.get(
                            "data", {}
                        ).get("output")
                        if (
                            output
                            and isinstance(output, dict)
                            and output.get("usage_metadata")
                        ):
                            completion_usage_metadata = (
                                self.convert_usage_meta_data_to_openai(
                                    usages=[output["usage_metadata"]]
                                )
                            )

                            # Handle the end of the chain event
                            chat_end_stream_response: ChatCompletionChunk = (
                                ChatCompletionChunk(
                                    id=request_id,
                                    created=int(time.time()),
                                    model=chat_request_wrapper.model,
                                    choices=[],
                                    usage=completion_usage_metadata,
                                    object="chat.completion.chunk",
                                )
                            )
                            yield f"data: {json.dumps(chat_end_stream_response.model_dump())}\n\n"
                    case "on_tool_start":
                        # Handle the start of the tool event
                        event_dict = cast(dict[str, Any], event_object)
                        tool_name: Optional[str] = event_dict.get("name", None)
                        tool_input: Dict[str, Any] | None = event_dict.get(
                            "data", {}
                        ).get("input")

                        # copy the tool_input to avoid modifying the original
                        tool_input_display = (
                            tool_input.copy() if tool_input is not None else None
                        )
                        # remove auth_token from tool_input
                        if tool_input_display and "auth_token" in tool_input_display:
                            tool_input_display["auth_token"] = "***"
                        if tool_input_display and "state" in tool_input_display:
                            tool_input_display["state"] = "***"

                        if tool_name:
                            logger.debug(
                                f"on_tool_start: {tool_name} {tool_input_display}"
                            )
                            chat_stream_response = ChatCompletionChunk(
                                id=request_id,
                                created=int(time.time()),
                                model=chat_request_wrapper.model,
                                choices=[
                                    ChunkChoice(
                                        index=0,
                                        delta=ChoiceDelta(
                                            role="assistant",
                                            content=f"\n\n> Running Agent {tool_name}: {tool_input_display}\n",
                                        ),
                                    )
                                ],
                                usage=CompletionUsage(
                                    prompt_tokens=0,
                                    completion_tokens=0,
                                    total_tokens=0,
                                ),
                                object="chat.completion.chunk",
                            )
                            yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"

                    case "on_tool_end":
                        # Handle the end of the tool event
                        event_dict = cast(dict[str, Any], event_object)
                        tool_message: ToolMessage | None = event_dict.get(
                            "data", {}
                        ).get("output")
                        if tool_message:
                            artifact: Optional[Any] = tool_message.artifact

                            # print(f"on_tool_end: {tool_message}")
                            return_raw_tool_output: bool = (
                                os.environ.get("RETURN_RAW_TOOL_OUTPUT", "0") == "1"
                            )
                            if artifact or return_raw_tool_output:
                                # tool_message_content_type = type(tool_message.content)
                                tool_message_content: str = (
                                    self.convert_message_content_into_string(
                                        tool_message=tool_message
                                    )
                                )
                                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                                    logger.info(
                                        f"Returning artifact: {artifact if artifact else tool_message_content}"
                                    )

                                token_count: int = self.token_reducer.count_tokens(
                                    tool_message_content
                                    if return_raw_tool_output
                                    else str(artifact)
                                )

                                tool_progress_message: str = (
                                    (
                                        f"```"
                                        f"\n==== Raw responses from Agent {tool_message.name} [tokens: {token_count}] ====="
                                        f"\n{tool_message_content}"
                                        f"\n==== End Raw responses from Agent {tool_message.name} [tokens: {token_count}] ====="
                                        f"\n```\n"
                                    )
                                    if return_raw_tool_output
                                    else f"\n> {artifact}"
                                    + (
                                        f" [tokens: {token_count}]"
                                        if logger.isEnabledFor(logging.DEBUG) > 0
                                        else ""
                                    )
                                )
                                chat_stream_response = ChatCompletionChunk(
                                    id=request_id,
                                    created=int(time.time()),
                                    model=chat_request_wrapper.model,
                                    choices=[
                                        ChunkChoice(
                                            index=0,
                                            delta=ChoiceDelta(
                                                role="assistant",
                                                content=tool_progress_message,
                                            ),
                                        )
                                    ],
                                    usage=CompletionUsage(
                                        prompt_tokens=0,
                                        completion_tokens=0,
                                        total_tokens=0,
                                    ),
                                    object="chat.completion.chunk",
                                )
                                yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"
                    case _:
                        # Handle other event types
                        pass
        except TokenRetrievalError as e:
            logger.exception(e, stack_info=True)
            message: str = f"Token retrieval error: {e}.  If you are running locally, your AWS session may have expired.  Please re-authenticate using `aws sso login --profile [role]`."
            chat_stream_response = ChatCompletionChunk(
                id=request_id,
                created=int(time.time()),
                model=chat_request_wrapper.model,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=f"\n{message}\n",
                        ),
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                ),
                object="chat.completion.chunk",
            )
            yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(
                f"Exception in _stream_resp_async_generator: {e}\n{tb}", exc_info=True
            )
            error_message = f"Error: {e}\nTraceback:\n{tb}"
            chat_stream_response = ChatCompletionChunk(
                id=request_id,
                created=int(time.time()),
                model=chat_request_wrapper.model,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=f"\n{error_message}\n",
                        ),
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=0, completion_tokens=0, total_tokens=0
                ),
                object="chat.completion.chunk",
            )
            yield f"data: {json.dumps(chat_stream_response.model_dump())}\n\n"

        yield "data: [DONE]\n\n"

    @staticmethod
    def convert_message_content_into_string(*, tool_message: ToolMessage) -> str:
        def safe_json(string: str) -> Any:
            try:
                return json.loads(string)
            except json.JSONDecodeError:
                return None

        if isinstance(tool_message.content, str):
            # the content is str then just return it
            # see if this is a json object embedded in text
            json_content: Any = safe_json(tool_message.content)
            if json_content is not None:
                if isinstance(json_content, dict):
                    if "result" in json_content:
                        # https://github.com/open-webui/open-webui/discussions/11981
                        return cast(str, json_content.get("result"))
            return tool_message.content

        if (
            isinstance(tool_message.content, list)
            and len(tool_message.content) == 1
            and isinstance(tool_message.content[0], dict)
            and "result" in tool_message.content[0]
        ):
            return cast(str, tool_message.content[0].get("result"))

        return (
            # otherwise if content is a list, convert each item to str and join the items with a space
            " ".join([str(c) for c in tool_message.content])
        )

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
                await self.get_streaming_response_async(
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
                # add usage metadata from each message into a total usage metadata
                total_usage_metadata: CompletionUsage = (
                    self.convert_usage_meta_data_to_openai(
                        usages=[
                            m.usage_metadata
                            for m in responses
                            if hasattr(m, "usage_metadata") and m.usage_metadata
                        ]
                    )
                )

                output_messages_raw: List[ChatCompletionMessage | None] = [
                    langchain_to_chat_message(m)
                    for m in responses
                    if isinstance(m, AIMessage) or isinstance(m, ToolMessage)
                ]
                output_messages: List[ChatCompletionMessage] = [
                    m for m in output_messages_raw if m is not None
                ]

                choices: List[Choice] = [
                    Choice(index=i, message=m, finish_reason="stop")
                    for i, m in enumerate(output_messages)
                ]

                choices_text = "\n".join([f"{c.message.content}" for c in choices])

                if json_output_requested:
                    # extract the json content from response and just return that
                    json_content_raw: Dict[str, Any] | List[Dict[str, Any]] | str = (
                        (JsonExtractor.extract_structured_output(text=choices_text))
                        if choices_text
                        else choices_text
                    )
                    json_content: str = json.dumps(json_content_raw)
                    choices = [
                        Choice(
                            index=i,
                            message=ChatCompletionMessage(
                                content=json_content, role="assistant"
                            ),
                            finish_reason="stop",
                        )
                        for i in range(1)
                    ]

                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1" and choices_text:
                    logger.info(f"Returning content: {choices_text}")

                chat_response: ChatCompletion = ChatCompletion(
                    id=request_information.request_id,
                    model=chat_request_wrapper.model,
                    choices=choices,
                    usage=total_usage_metadata,
                    created=int(time.time()),
                    object="chat.completion",
                )
                return JSONResponse(content=chat_response.model_dump())
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
        response_format: ResponseFormat | NotGiven = (
            chat_request_wrapper.response_format
        )
        if isinstance(response_format, NotGiven):
            return chat_request_wrapper, json_response_requested

        match response_format.get("type", None):
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
                json_response_format: ResponseFormatJSONSchema = cast(
                    ResponseFormatJSONSchema,
                    response_format,
                )
                json_schema: JSONSchema | None = json_response_format.get("json_schema")
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
                raise ValueError(
                    f"Unexpected response format type: {response_format.get('type', None)}"
                )

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
        output: Dict[str, Any] = await compiled_state_graph.ainvoke(
            input=input_, config=config
        )
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
        messages_: List[BaseMessage] = [m.to_langchain_message() for m in messages]

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

    async def create_graph_for_llm_async(
        self,
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
    def add_completion_usage(
        *, original: CompletionUsage, new_one: CompletionUsage
    ) -> CompletionUsage:
        """
        Add completion usage metadata.

        Args:
            original: The original completion usage metadata.
            new_one: The new completion usage metadata.

        Returns:
            The completion usage metadata.
        """
        return CompletionUsage(
            prompt_tokens=original.prompt_tokens + new_one.prompt_tokens,
            completion_tokens=original.completion_tokens + new_one.completion_tokens,
            total_tokens=original.total_tokens + new_one.total_tokens,
        )

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
