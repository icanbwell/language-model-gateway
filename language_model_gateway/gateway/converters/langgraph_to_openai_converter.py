import json
import logging
import os
import re
import time
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
from langchain_community.adapters.openai import convert_openai_messages
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
from langmem import create_search_memory_tool
from openai import NotGiven, NOT_GIVEN
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionSystemMessageParam,
)
from openai.types.chat import ChatCompletionMessageParam
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
from language_model_gateway.gateway.schema.openai.completions import (
    ChatRequest,
)
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.tools.get_user_info_tool import GetUserInfoTool
from language_model_gateway.gateway.tools.memories.store_user_profile_tool import (
    StoreUserProfileTool,
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

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangGraphToOpenAIConverter:
    def __init__(self, *, environment_variables: EnvironmentVariables) -> None:
        self.environment_variables: EnvironmentVariables = environment_variables

    async def _stream_resp_async_generator(
        self,
        *,
        request: ChatRequest,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: List[ChatCompletionMessageParam],
        request_information: RequestInformation,
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously generate streaming responses from the agent.

        Args:
            request: The chat request.
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
                request=request,
                compiled_state_graph=compiled_state_graph,
                messages=messages,
                request_information=request_information,
            ):
                if not event:
                    continue

                event_type: str = event["event"]

                # events are described here: https://python.langchain.com/docs/how_to/streaming/#using-stream-events

                # print(f"===== {event_type} =====\n{event}\n")

                match event_type:
                    case "on_chain_start":
                        # Handle the start of the chain event
                        pass
                    case "on_chain_stream":
                        # Handle the chain stream event.  Be sure not to write duplicate responses to what is done in the on_chat_model_stream event.
                        pass
                    case "on_chat_model_stream":
                        # Handle the chat model stream event
                        chunk: AIMessageChunk | None = event.get("data", {}).get(
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

                            assert isinstance(content_text, str), (
                                f"content_text: {content_text} (type: {type(content_text)})"
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
                                        model=request["model"],
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
                        output: Dict[str, Any] | str | None = event.get("data", {}).get(
                            "output"
                        )
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
                                    model=request["model"],
                                    choices=[],
                                    usage=completion_usage_metadata,
                                    object="chat.completion.chunk",
                                )
                            )
                            yield f"data: {json.dumps(chat_end_stream_response.model_dump())}\n\n"
                    case "on_tool_start":
                        # Handle the start of the tool event
                        tool_name: Optional[str] = event.get("name", None)
                        tool_input: Dict[str, Any] | None = event.get("data", {}).get(
                            "input"
                        )

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
                                model=request["model"],
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
                        tool_message: ToolMessage | None = event.get("data", {}).get(
                            "output"
                        )
                        if tool_message:
                            artifact: Optional[Any] = tool_message.artifact

                            # print(f"on_tool_end: {tool_message}")
                            if (
                                not artifact
                                and os.environ.get("RETURN_RAW_TOOL_OUTPUT", "0") == "1"
                            ):
                                artifact = tool_message.content

                            if artifact:
                                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                                    logger.info(f"Returning artifact: {artifact}")

                                chat_stream_response = ChatCompletionChunk(
                                    id=request_id,
                                    created=int(time.time()),
                                    model=request["model"],
                                    choices=[
                                        ChunkChoice(
                                            index=0,
                                            delta=ChoiceDelta(
                                                role="assistant",
                                                content=f"\n> ==== Raw response from tool {tool_message.name} =====\n",
                                            ),
                                        ),
                                        ChunkChoice(
                                            index=0,
                                            delta=ChoiceDelta(
                                                role="assistant",
                                                content=f"\n> {artifact}\n",
                                            ),
                                        ),
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
                model=request["model"],
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
            chat_stream_response = ChatCompletionChunk(
                id=request_id,
                created=int(time.time()),
                model=request["model"],
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=f"\nError:\n{e}\n",
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

    async def call_agent_with_input(
        self,
        *,
        chat_request: ChatRequest,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: List[ChatCompletionSystemMessageParam],
        request_information: RequestInformation,
    ) -> StreamingResponse | JSONResponse:
        """
        Call the agent with the provided input and return the response.

        Args:
            chat_request: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.

        Returns:
            The response as a StreamingResponse or JSONResponse.
        """
        assert chat_request is not None

        if chat_request.get("stream"):
            return StreamingResponse(
                await self.get_streaming_response_async(
                    request=chat_request,
                    compiled_state_graph=compiled_state_graph,
                    system_messages=system_messages,
                    request_information=request_information,
                ),
                media_type="text/event-stream",
            )
        else:
            try:
                json_output_requested: bool
                chat_request, json_output_requested = self.add_system_messages_for_json(
                    chat_request=chat_request
                )

                chat_request = self.add_system_message_for_user_info(
                    chat_request=chat_request,
                    user_id=request_information.user_id,
                    user_name=request_information.user_name,
                    email=request_information.user_email,
                )

                responses: List[AnyMessage] = await self.ainvoke(
                    compiled_state_graph=compiled_state_graph,
                    request=chat_request,
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
                    model=chat_request["model"],
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
                import traceback

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
        chat_request: ChatRequest,
        user_id: Optional[str],
        user_name: Optional[str],
        email: Optional[str],
    ) -> ChatRequest:
        content: str = (
            f"You are interacting with user_id: {user_id} who is named {user_name} and has email {email}"
            if user_id
            else "You are interacting with an anonymous user"
        )

        new_system_message: ChatCompletionSystemMessageParam = (
            ChatCompletionSystemMessageParam(role="system", content=content)
        )
        chat_request["messages"] = [r for r in chat_request["messages"]] + [
            new_system_message
        ]
        return chat_request

    @staticmethod
    def add_system_messages_for_json(
        *, chat_request: ChatRequest
    ) -> Tuple[ChatRequest, bool]:
        """
        If the user is requesting json_object or json_schema output, add system messages to the chat request
        to generate JSON output.


        :param chat_request:
        :return:
        """
        json_response_requested: bool = False
        response_format: ResponseFormat | NotGiven = chat_request.get(
            "response_format", NOT_GIVEN
        )
        if isinstance(response_format, NotGiven):
            return chat_request, json_response_requested

        match response_format.get("type", None):
            case "text":
                return chat_request, json_response_requested
            case "json_object":
                json_response_requested = True
                json_object_system_message_text: str = """
                Respond only with a JSON object or array.

                Output follows this example format:
                <json>
                json  here
                </json>"""
                json_object_system_message: ChatCompletionSystemMessageParam = (
                    ChatCompletionSystemMessageParam(
                        role="system", content=json_object_system_message_text
                    )
                )
                chat_request["messages"] = [r for r in chat_request["messages"]] + [
                    json_object_system_message
                ]
                return chat_request, json_response_requested
            case "json_schema":
                json_response_requested = True
                json_response_format: ResponseFormatJSONSchema = cast(
                    ResponseFormatJSONSchema,
                    response_format,
                )
                json_schema: JSONSchema | None = json_response_format.get("json_schema")
                assert json_schema is not None, (
                    "json_schema should be specified in response_format if type is json_schema"
                )
                json_schema_system_message_text: str = f"""
                Respond only with a JSON object or array using the provided schema:
                ```{json_schema}```

                Output follows this example format:
                <json>
                json  here
                </json>"""
                json_schema_system_message: ChatCompletionSystemMessageParam = (
                    ChatCompletionSystemMessageParam(
                        role="system", content=json_schema_system_message_text
                    )
                )
                chat_request["messages"] = [r for r in chat_request["messages"]] + [
                    json_schema_system_message
                ]
                return chat_request, json_response_requested
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
        request: ChatRequest,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: List[ChatCompletionSystemMessageParam],
        request_information: RequestInformation,
    ) -> AsyncGenerator[str, None]:
        """
        Get the streaming response asynchronously.

        Args:
            request: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The list of chat completion message parameters.
            request_information: The request information.

        Returns:
            The streaming response as an async generator.
        """

        new_messages: List[ChatCompletionMessageParam] = [
            m for m in request["messages"]
        ]
        messages: List[ChatCompletionMessageParam] = [
            s for s in system_messages
        ] + new_messages

        logger.info(f"Streaming response {request_information.request_id} from agent")
        generator: AsyncGenerator[str, None] = self._stream_resp_async_generator(
            request=request,
            compiled_state_graph=compiled_state_graph,
            messages=messages,
            request_information=request_information,
        )
        return generator

    # noinspection PyMethodMayBeStatic
    async def _run_graph_with_messages_async(
        self,
        *,
        chat_request: ChatRequest,
        messages: List[BaseMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the graph with the provided messages asynchronously.

        Args:
            messages: The list of role and incoming message type tuples.
            compiled_state_graph: The compiled state graph.
            chat_request: The chat request.
            request_information: The request information.

        Returns:
            The list of any messages.
        """

        input_: MyMessagesState = self.create_state(
            chat_request=chat_request,
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
        request: ChatRequest,
        messages: List[BaseMessage],
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream the graph with the provided messages asynchronously.

        Args:
            request: The chat request.
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
                chat_request=request,
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
        request: ChatRequest,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        system_messages: Iterable[ChatCompletionSystemMessageParam],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the agent asynchronously.

        Args:
            request: The chat request.
            compiled_state_graph: The compiled state graph.
            system_messages: The iterable of chat completion message parameters.
            request_information: The request information.

        Returns:
            The list of any messages.
        """
        assert request is not None

        new_messages: List[ChatCompletionMessageParam] = [
            m for m in request["messages"]
        ]
        messages: List[ChatCompletionMessageParam] = [
            s for s in system_messages
        ] + new_messages

        return await self._run_graph_with_messages_async(
            chat_request=request,
            compiled_state_graph=compiled_state_graph,
            messages=self.create_messages_for_graph(messages=messages),
            request_information=request_information,
        )

    async def astream_events(
        self,
        *,
        request: ChatRequest,
        request_information: RequestInformation,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        messages: Iterable[ChatCompletionMessageParam],
    ) -> AsyncGenerator[StandardStreamEvent | CustomStreamEvent, None]:
        """
        Stream events asynchronously.

        Args:
            request: The chat request.
            compiled_state_graph: The compiled state graph.
            messages: The iterable of chat completion message parameters.
            request_information: The request information.

        Yields:
            The standard or custom stream event.
        """
        event: StandardStreamEvent | CustomStreamEvent
        async for event in self._stream_graph_with_messages_async(
            request=request,
            compiled_state_graph=compiled_state_graph,
            messages=self.create_messages_for_graph(messages=messages),
            request_information=request_information,
        ):
            yield event

    # noinspection PyMethodMayBeStatic
    def create_messages_for_graph(
        self, *, messages: Iterable[ChatCompletionMessageParam]
    ) -> List[BaseMessage]:
        """
        Create messages for the graph.

        Args:
            messages: The iterable of chat completion message parameters.

        Returns:
            The list of role and incoming message type tuples.
        """
        messages_: List[BaseMessage] = convert_openai_messages(
            messages=[cast(Dict[str, Any], m) for m in messages]
        )
        return messages_

    async def run_graph_async(
        self,
        *,
        request: ChatRequest,
        compiled_state_graph: CompiledStateGraph[MyMessagesState],
        request_information: RequestInformation,
    ) -> List[AnyMessage]:
        """
        Run the graph asynchronously.

        Args:
            request: The chat request.
            compiled_state_graph: The compiled state graph.
            request_information: The request information.

        Returns:
            The list of any messages.
        """
        messages: List[BaseMessage] = self.create_messages_for_graph(
            messages=request["messages"]
        )

        output_messages: List[AnyMessage] = await self._run_graph_with_messages_async(
            chat_request=request,
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

        if self.environment_variables.enable_llm_memory and store is not None:
            # Memory tools use LangGraph's BaseStore for persistence (4)
            user_profile_namespace = ("memories", "{user_id}", "user_profile")
            # memories_namespace = ("memories", "{user_id}", "memories")
            tools = (
                list(tools)
                + [
                    StoreUserProfileTool(  # All memories saved to this tool will live within this namespace
                        # The brackets will be populated at runtime by the configurable values
                        namespace=user_profile_namespace,
                        # description="Update the existing user profile (or create a new one if it doesn't exist) based on the shared information.  Create one entry per user.",
                    ),
                    # ManageMemoryTool(namespace=memories_namespace),
                    create_search_memory_tool(namespace=user_profile_namespace),
                    GetUserInfoTool(),
                ]
            )

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
        chat_request: ChatRequest,
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
