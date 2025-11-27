import json
import logging
import os
import time
from typing import (
    Any,
    List,
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
from langchain_core.messages.ai import UsageMetadata
from langchain_core.runnables.schema import CustomStreamEvent, StandardStreamEvent
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionChunk,
)
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice

from language_model_gateway.gateway.converters.streaming_utils import (
    format_chat_completion_chunk_sse,
)
from language_model_gateway.gateway.schema.openai.completions import (
    ChatRequest,
)
from language_model_gateway.gateway.utilities.chat_message_helpers import (
    convert_message_content_to_string,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangGraphStreamingManager:
    def __init__(self, token_reducer: TokenReducer) -> None:
        self.token_reducer: TokenReducer = token_reducer

    async def handle_langchain_event(
        self,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
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
                chunk: AIMessageChunk | None = event_dict.get("data", {}).get("chunk")
                if chunk is not None:
                    content: str | list[str | dict[str, Any]] = chunk.content

                    # print(f"chunk: {chunk}")

                    usage_metadata = chunk.usage_metadata
                    completion_usage_metadata = self.convert_usage_meta_data_to_openai(
                        usages=[usage_metadata] if usage_metadata else []
                    )

                    content_text: str = convert_message_content_to_string(content)
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
                        yield format_chat_completion_chunk_sse(
                            chat_model_stream_response.model_dump()
                        )
            case "on_chain_end":
                # print(f"===== {event_type} =====\n{event}\n")
                event_dict = cast(dict[str, Any], event_object)
                output: Dict[str, Any] | str | None = event_dict.get("data", {}).get(
                    "output"
                )
                if output and isinstance(output, dict) and output.get("usage_metadata"):
                    completion_usage_metadata = self.convert_usage_meta_data_to_openai(
                        usages=[output["usage_metadata"]]
                    )

                    # Handle the end of the chain event
                    chat_end_stream_response: ChatCompletionChunk = ChatCompletionChunk(
                        id=request_id,
                        created=int(time.time()),
                        model=request["model"],
                        choices=[],
                        usage=completion_usage_metadata,
                        object="chat.completion.chunk",
                    )
                    yield format_chat_completion_chunk_sse(
                        chat_end_stream_response.model_dump()
                    )
            case "on_tool_start":
                # Handle the start of the tool event
                event_dict = cast(dict[str, Any], event_object)
                tool_name: Optional[str] = event_dict.get("name", None)
                tool_input: Dict[str, Any] | None = event_dict.get("data", {}).get(
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

                # Track start time for this tool invocation
                tool_key = self.make_tool_key(tool_name, tool_input)
                tool_start_times[tool_key] = time.time()

                if tool_name:
                    logger.debug(f"on_tool_start: {tool_name} {tool_input_display}")
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
                    yield format_chat_completion_chunk_sse(
                        chat_stream_response.model_dump()
                    )

            case "on_tool_end":
                # Handle the end of the tool event
                event_dict = cast(dict[str, Any], event_object)
                tool_message: ToolMessage | None = event_dict.get("data", {}).get(
                    "output"
                )
                # Try to get tool name and input from tool_message or event_dict
                tool_name2: Optional[str] = None
                tool_input2: Optional[Dict[str, Any]] = None
                if tool_message:
                    tool_name2 = getattr(tool_message, "name", None)
                    tool_input2 = getattr(tool_message, "input", None)
                if not tool_name2:
                    tool_name2 = event_dict.get("name", None)
                if not tool_input2:
                    tool_input2 = event_dict.get("data", {}).get("input")
                tool_key = self.make_tool_key(tool_name2, tool_input2)
                start_time = tool_start_times.pop(tool_key, None)
                runtime_str = ""
                if start_time is not None:
                    elapsed = time.time() - start_time
                    runtime_str = f"{elapsed:.2f}s"
                    logger.info(
                        f"Tool {tool_name2} completed in {elapsed:.2f} seconds."
                    )
                else:
                    logger.warning(
                        f"Tool {tool_name2} end event received without matching start event."
                    )
                if tool_message:
                    artifact: Optional[Any] = tool_message.artifact
                    return_raw_tool_output: bool = (
                        os.environ.get("RETURN_RAW_TOOL_OUTPUT", "0") == "1"
                    )
                    if artifact or return_raw_tool_output:
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
                                f"\n==== Raw responses from Agent {tool_message.name} [tokens: {token_count}] [runtime: {runtime_str}] ====="
                                f"\n{tool_message_content}"
                                f"\n==== End Raw responses from Agent {tool_message.name} [tokens: {token_count}] [runtime: {runtime_str}] ====="
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
                            model=request["model"],
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
                        yield format_chat_completion_chunk_sse(
                            chat_stream_response.model_dump()
                        )
                else:
                    logger.debug("on_tool_end: no tool message output")
                    chat_stream_response = ChatCompletionChunk(
                        id=request_id,
                        created=int(time.time()),
                        model=request["model"],
                        choices=[
                            ChunkChoice(
                                index=0,
                                delta=ChoiceDelta(
                                    role="assistant",
                                    content=f"\n\n> Tool completed with no output.{runtime_str}\n",
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
                    yield format_chat_completion_chunk_sse(
                        chat_stream_response.model_dump()
                    )

            case _:
                # Handle other event types
                pass

            # noinspection PyMethodMayBeStatic

    @staticmethod
    def convert_usage_meta_data_to_openai(
        *, usages: List[UsageMetadata]
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

    @staticmethod
    def make_tool_key(
        tool_name1: Optional[str], tool_input1: Optional[Dict[str, Any]]
    ) -> str:
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
                    text_message: str = ""
                    if "result" in json_content:
                        # https://github.com/open-webui/open-webui/discussions/11981
                        result = json_content.get("result")
                        if result:
                            text_message += cast(str, json_content.get("result"))
                    if "error" in json_content:
                        error_message = json_content.get("error", "")
                        if error_message:
                            text_message += f"\nError: {error_message}\n"
                    if "meta" in json_content:
                        meta = json_content.get("meta", {})
                        if isinstance(meta, dict) and len(meta) > 0:
                            text_message += "\nMetadata:\n"
                            for key, value in meta.items():
                                text_message += f"- {key}: {value}\n"
                    if "urls" in json_content:
                        urls = json_content.get("urls", [])
                        if isinstance(urls, list) and len(urls) > 0:
                            text_message += "\nRelated URLs:\n"
                            for url in urls:
                                text_message += f"- {url}\n"

                    # if none of the above fields are present, return the original content
                    if not json_content.get("result") and not json_content.get("error"):
                        return tool_message.content
                    return text_message
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
