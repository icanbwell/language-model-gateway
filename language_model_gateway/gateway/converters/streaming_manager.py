import copy  # For deepcopy
import json
import logging
import os
import time
from typing import (
    Any,
    cast,
    Optional,
)
from typing import (
    Dict,
    AsyncGenerator,
)

from langchain_core.messages import AIMessageChunk
from langchain_core.messages import (
    ToolMessage,
)
from langchain_core.runnables.schema import CustomStreamEvent, StandardStreamEvent

from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.structures.request_information import (
    RequestInformation,
)
from language_model_gateway.gateway.utilities.chat_message_helpers import (
    convert_message_content_to_string,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)
from langchain_core.messages import BaseMessage
from langchain_core.runnables.schema import (
    EventData,
)

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangGraphStreamingManager:
    """
    Dispatches LangGraph streaming events into OpenAI-compatible SSE chunks.

    This class listens for events emitted by LangGraph's `astream_events` and
    translates them into SSE messages that OpenWebUI can display. Key events:

    - ``on_chat_model_stream`` – Token-by-token LLM output (main response text).
    - ``on_tool_start`` / ``on_tool_end`` – MCP tool invocation lifecycle.
    - ``on_tool_error`` – Errors during tool execution.
    - ``on_chain_end`` – Final usage metadata for the request.

    Instantiated via DI container (`ContainerFactory`) and injected into
    `LangGraphToOpenAIConverter`.
    """

    def __init__(
        self,
        *,
        token_reducer: TokenReducer,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
    ) -> None:
        self.token_reducer: TokenReducer = token_reducer
        if self.token_reducer is None:
            raise ValueError("token_reducer must not be None")
        if not isinstance(self.token_reducer, TokenReducer):
            raise TypeError("token_reducer must be an instance of TokenReducer")

        self.environment_variables: LanguageModelGatewayEnvironmentVariables = (
            environment_variables
        )
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables,
            LanguageModelGatewayEnvironmentVariables,
        ):
            raise TypeError(
                "environment_variables must be an instance of LanguageModelGatewayEnvironmentVariables"
            )

    async def handle_langchain_event(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        """Route a single LangGraph event to the appropriate handler and yield SSE chunks."""
        try:
            event_type: str = event["event"]
            # logger.debug(f"Received event type: {event_type}: {event}")
            # Events defined here:
            # https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.BaseChatModel.astream_events
            # https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events
            match event_type:
                case "on_chat_model_start":
                    async for chunk in self._handle_on_chat_model_start(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                    ):
                        if chunk:
                            yield chunk
                case "on_chat_model_end":
                    pass
                case "on_chain_start":
                    # async for chunk in self._handle_on_chain_start(
                    #     event=event,
                    #     chat_request_wrapper=chat_request_wrapper,
                    #     request_id=request_id,
                    #     messages=messages,
                    # ):
                    #     if chunk:
                    #         yield chunk
                    pass
                case "on_chain_stream":
                    pass
                case "on_chat_model_stream":
                    async for chunk in self._handle_on_chat_model_stream(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                    ):
                        if chunk:
                            yield chunk
                case "on_chain_end":
                    async for chunk in self._handle_on_chain_end(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                    ):
                        if chunk:
                            yield chunk
                case "on_tool_start":
                    async for chunk in self._handle_on_tool_start(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                        tool_start_times=tool_start_times,
                    ):
                        if chunk:
                            yield chunk
                case "on_tool_end":
                    async for chunk in self._handle_on_tool_end(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                        tool_start_times=tool_start_times,
                    ):
                        if chunk:
                            yield chunk
                case "on_tool_error":
                    async for chunk in self._handle_on_tool_error(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_information=request_information,
                        tool_start_times=tool_start_times,
                    ):
                        if chunk:
                            yield chunk
                case _:
                    logger.debug(f"Skipped event type: {event_type}")
        except Exception as e:
            logger.exception(f"Error handling langchain event: {e}")

    async def _handle_on_chat_model_stream(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
    ) -> AsyncGenerator[str, None]:
        """Yield SSE chunk for each LLM token received (main response text)."""
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        data = event["data"] if "data" in event else {}
        chunk: AIMessageChunk | None = data.get("chunk")
        if chunk is not None:
            content: str | list[str | dict[str, Any]] = chunk.content
            content_text: str = convert_message_content_to_string(content)
            if not isinstance(content_text, str):
                raise TypeError(f"content_text must be str, got {type(content_text)}")
            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1" and content_text:
                logger.debug(f"Returning content: {content_text}")
            if content_text:
                yield chat_request_wrapper.create_sse_message(
                    request_id=request_information.request_id,
                    content=content_text,
                    usage_metadata=chunk.usage_metadata,
                    source="on_chat_model_stream",
                )

    async def _handle_on_chain_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
    ) -> AsyncGenerator[str, None]:
        """Emit final SSE message with usage metadata when the LangGraph chain completes."""
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        data = event["data"] if "data" in event else {}
        output: Dict[str, Any] | str | None = data.get("output")
        if output and isinstance(output, dict) and "usage_metadata" in output:
            yield chat_request_wrapper.create_final_sse_message(
                request_id=request_information.request_id,
                usage_metadata=output["usage_metadata"],
                source="on_chain_end",
            )

    async def _handle_on_tool_start(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        """Record tool start time and emit debug SSE showing which MCP tool is running."""
        tool_name: Optional[str] = event["name"] if "name" in event else None
        logger.debug(f"on_tool_start: {tool_name}: {event}")
        data = event["data"] if "data" in event else {}
        tool_input: Optional[Dict[str, Any]] = data.get("input")
        tool_input_display: Optional[Dict[str, Any]] = (
            tool_input.copy() if tool_input is not None else None
        )
        if tool_input_display and "auth_token" in tool_input_display:
            tool_input_display["auth_token"] = "***"
        if tool_input_display and "state" in tool_input_display:
            tool_input_display["state"] = "***"
        if tool_input_display and "runtime" in tool_input_display:
            tool_input_display.pop(
                "runtime"
            )  # runtime has the chat history and other data we don't need to show
        tool_key: str = self.make_tool_key(tool_name, tool_input)
        tool_start_times[tool_key] = time.time()
        if tool_name:
            logger.debug(f"on_tool_start: {tool_name} {tool_input_display}")
            content_text: str = (
                f"\n\n> Running Agent {tool_name}: {tool_input_display}\n"
            )
            debug_message = chat_request_wrapper.create_debug_sse_message(
                request_id=request_information.request_id,
                content=content_text,
                usage_metadata=None,
                source="on_tool_start",
            )
            if debug_message:
                yield debug_message

    async def _handle_on_tool_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        """Emit debug SSE when MCP tool completes, including runtime and optional raw output."""
        logger.debug(f"on_tool_end: {event}")
        data = event["data"] if "data" in event else {}
        tool_message: Optional[ToolMessage] = data.get("output")
        tool_name2: Optional[str] = None
        tool_input2: Optional[Dict[str, Any]] = None
        if tool_message:
            tool_name2 = getattr(tool_message, "name", None)
            tool_input2 = getattr(tool_message, "input", None)
        if not tool_name2:
            tool_name2 = event["name"] if "name" in event else None
        if not tool_input2:
            tool_input2 = data.get("input")
        tool_key: str = self.make_tool_key(tool_name2, tool_input2)
        start_time: Optional[float] = tool_start_times.pop(tool_key, None)
        runtime_str: str = ""
        if start_time is not None:
            elapsed: float = time.time() - start_time
            runtime_str = f"{elapsed:.2f}s"
            logger.debug(f"Tool {tool_name2} completed in {elapsed:.2f} seconds.")
        else:
            logger.warning(
                f"Tool {tool_name2} end event received without matching start event."
            )
        if tool_message:
            artifact: Optional[Any] = tool_message.artifact

            logger.debug(
                f"Tool {tool_name2} has artifact of type {type(artifact)}: {artifact}"
            )

            return_raw_tool_output: bool = (
                os.environ.get("RETURN_RAW_TOOL_OUTPUT", "0") == "1"
            )
            structured_data: dict[str, Any] | None = (
                artifact if isinstance(artifact, dict) else None
            )
            structured_data_without_result: dict[str, Any] | None = (
                copy.deepcopy(structured_data) if structured_data is not None else None
            )
            if structured_data_without_result:
                structured_data_without_result.pop("result", None)
                structured_content = structured_data_without_result.get(
                    "structured_content"
                )
                # Only pop from structured_content if it is a dict
                if isinstance(structured_content, dict):
                    structured_content.pop("result", None)

            if return_raw_tool_output:
                tool_message_content: str = self.convert_message_content_into_string(
                    tool_message=tool_message
                )

                token_count: int = self.token_reducer.count_tokens(tool_message_content)

                tool_progress_message: str = (
                    (
                        f"""```
==== Raw responses from Agent {tool_message.name} [tokens: {token_count}] [runtime: {runtime_str}] =====
{tool_message_content}
==== End Raw responses from Agent {tool_message.name} [tokens: {token_count}] [runtime: {runtime_str}] =====
```
"""
                    )
                    if return_raw_tool_output
                    else f"\n> {artifact}" + f" [tokens: {token_count}]"
                )
                debug_message = chat_request_wrapper.create_debug_sse_message(
                    request_id=request_information.request_id,
                    content=tool_progress_message,
                    usage_metadata=None,
                    source="on_tool_end",
                )
                if debug_message:
                    yield debug_message
        else:
            logger.debug("on_tool_end: no tool message output")
            content_text = f"\n\n> Tool completed with no output.{runtime_str}\n"
            debug_message = chat_request_wrapper.create_debug_sse_message(
                request_id=request_information.request_id,
                content=content_text,
                usage_metadata=None,
                source="on_tool_end",
            )
            if debug_message:
                yield debug_message

    # noinspection PyMethodMayBeStatic
    async def _handle_on_chat_model_start(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
    ) -> AsyncGenerator[str | None, None]:
        """Emit debug SSE listing input messages when debug logging is enabled (skipped otherwise)."""
        if not request_information.enable_debug_logging:
            return

        data: EventData = event["data"] if "data" in event else {}
        # {
        #     "event": "on_chat_model_start",
        #     "name": str,                    # Name of the chat model (e.g., "ChatOpenAI", "gpt-4")
        #     "run_id": str,                  # Unique UUID for this execution
        #     "parent_ids": List[str],        # List of parent run IDs (v2 only)
        #     "tags": List[str],              # Tags for filtering/organization
        #     "metadata": Dict[str, Any],     # Additional metadata
        #     "data": {
        #         "input": {
        #             "messages": List[List[BaseMessage]]  # The input messages
        #         }
        #     }
        # }
        input_messages_list: list[list[BaseMessage]] = cast(
            list[list[BaseMessage]],
            cast(dict[str, Any], data.get("input", {})).get("messages", []),
        )
        input_messages: list[BaseMessage] = (
            input_messages_list[0] if input_messages_list else []
        )
        # append all the messages into content_text
        content_text = "```\n"
        content_text += "> Starting new chat_model with messages:\n"
        for message_number, input_message in enumerate(input_messages):
            content_text += (
                f"--- Message {message_number + 1} by {input_message.type} ---\n"
            )
            content_text += f"{input_message.content}\n"
        content_text += "```\n"

        yield chat_request_wrapper.create_debug_sse_message(
            request_id=request_information.request_id,
            content=content_text,
            usage_metadata=None,
            source="on_chat_model_start",
        )

    @staticmethod
    def _format_text_resource_contents(text: str) -> str:
        """Extract JSON fields (result, error, meta, urls) from text for human-readable output."""
        result = ""
        json_object: Any = LangGraphStreamingManager.safe_json(text)
        if json_object is not None and isinstance(json_object, dict):
            if "result" in json_object:
                result += str(json_object.get("result")) + "\n"
            if "error" in json_object:
                result += "Error: " + str(json_object.get("error")) + "\n"
            if "meta" in json_object:
                meta = json_object.get("meta", {})
                if isinstance(meta, dict) and len(meta) > 0:
                    result += "Metadata:\n"
                    for key, value in meta.items():
                        result += f"- {key}: {value}\n"
            if "urls" in json_object:
                urls = json_object.get("urls", [])
                if isinstance(urls, list) and len(urls) > 0:
                    result += "Related URLs:\n"
                    for url in urls:
                        result += f"- {url}\n"
            if "result" not in json_object and "error" not in json_object:
                result += text + "\n"
        else:
            result += text + "\n"
        return result

    async def _handle_on_tool_error(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_information: RequestInformation,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        """Emit SSE when an MCP tool raises an error, including runtime if available."""
        # Extract error details
        tool_name: Optional[str] = event["name"] if "name" in event else None
        data = event["data"] if "data" in event else {}
        error_message: BaseException | Any | str = data.get("error") or str(event)
        runtime_str: str = ""
        tool_key: str = self.make_tool_key(tool_name, data.get("input"))
        start_time: Optional[float] = tool_start_times.pop(tool_key, None)
        if start_time is not None:
            elapsed: float = time.time() - start_time
            runtime_str = f"{elapsed:.2f}s"
        logger.error(
            f"Tool error in {tool_name}: {error_message} [runtime: {runtime_str}]"
        )
        content_text: str = f"\n\n> Tool {tool_name} encountered an error: {error_message} [runtime: {runtime_str}]\n"
        yield chat_request_wrapper.create_sse_message(
            request_id=request_information.request_id,
            content=content_text,
            usage_metadata=None,
            source="on_tool_error",
        )

    @staticmethod
    def make_tool_key(
        tool_name1: Optional[str], tool_input1: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a unique key for a tool invocation to correlate start/end events."""
        # Use tool name and a hash of the input for uniqueness
        if tool_name1 is None:
            tool_name1 = "unknown"
        # noinspection PyBroadException
        try:
            tool_input_str = json.dumps(tool_input1, sort_keys=True, default=str)
        except Exception:
            tool_input_str = str(tool_input1)
        return f"{tool_name1}:{hash(tool_input_str)}"

    @staticmethod
    def safe_json(string: str) -> Any:
        """Parse JSON string, returning None on failure instead of raising."""
        try:
            return json.loads(string)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def convert_message_content_into_string(*, tool_message: ToolMessage) -> str:
        """Convert a ToolMessage's content to a string, extracting JSON result if present."""
        if isinstance(tool_message.content, str):
            # the content is str then just return it
            # see if this is a json object embedded in text
            return LangGraphStreamingManager._format_text_resource_contents(
                text=tool_message.content
            )

        # tool_message.content is a list of dicts (TextContent) where the text field
        # is a stringified json of the structured content
        if (
            isinstance(tool_message.content, list)
            and len(tool_message.content) == 1
            and isinstance(tool_message.content[0], dict)
            and "text" in tool_message.content[0]
        ):
            text = tool_message.content[0]["text"]
            # see if text is json
            json_object: dict[str, Any] = LangGraphStreamingManager.safe_json(text)
            if json_object is not None and isinstance(json_object, dict):
                if "result" in json_object:
                    return cast(str, json_object.get("result"))

        return (
            # otherwise if content is a list, convert each item to str and join the items with a space
            " ".join([str(c) for c in tool_message.content])
        )

    @staticmethod
    def get_structured_content_from_tool_message(
        *, tool_message: ToolMessage
    ) -> dict[str, Any] | None:
        """Extract structured dict content from a ToolMessage if available."""
        content_dict: Dict[str, Any] | None = None
        if isinstance(tool_message.content, dict):
            content_dict = tool_message.content
        elif (
            isinstance(tool_message.content, list)
            and len(tool_message.content) == 1
            and isinstance(tool_message.content[0], dict)
        ):
            content_dict = tool_message.content[0]
        return content_dict
