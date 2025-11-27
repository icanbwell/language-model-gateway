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
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
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
    def __init__(
        self, *, token_reducer: TokenReducer, file_manager_factory: FileManagerFactory
    ) -> None:
        self.token_reducer: TokenReducer = token_reducer
        if self.token_reducer is None:
            raise ValueError("token_reducer must not be None")
        if not isinstance(self.token_reducer, TokenReducer):
            raise TypeError("token_reducer must be an instance of TokenReducer")

        self.file_manager_factory: FileManagerFactory = file_manager_factory
        if self.file_manager_factory is None:
            raise ValueError("file_manager_factory must not be None")
        if not isinstance(self.file_manager_factory, FileManagerFactory):
            raise TypeError(
                "file_manager_factory must be an instance of FileManagerFactory"
            )

    async def handle_langchain_event(
        self,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        event_type: str = event["event"]
        # Events defined here:
        # https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.BaseChatModel.astream_events
        match event_type:
            case "on_chain_start":
                pass
            case "on_chain_stream":
                pass
            case "on_chat_model_stream":
                async for chunk in self._handle_on_chat_model_stream(
                    event=event, request=request, request_id=request_id
                ):
                    yield chunk
            case "on_chain_end":
                async for chunk in self._handle_on_chain_end(
                    event=event, request=request, request_id=request_id
                ):
                    yield chunk
            case "on_tool_start":
                async for chunk in self._handle_on_tool_start(
                    event=event,
                    request=request,
                    request_id=request_id,
                    tool_start_times=tool_start_times,
                ):
                    yield chunk
            case "on_tool_end":
                async for chunk in self._handle_on_tool_end(
                    event=event,
                    request=request,
                    request_id=request_id,
                    tool_start_times=tool_start_times,
                ):
                    yield chunk
            case _:
                pass

    async def _handle_on_chat_model_stream(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
    ) -> AsyncGenerator[str, None]:
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        data = event["data"] if "data" in event else {}
        chunk: AIMessageChunk | None = data.get("chunk")
        if chunk is not None:
            content: str | list[str | dict[str, Any]] = chunk.content
            usage_metadata: Optional[UsageMetadata] = chunk.usage_metadata
            completion_usage_metadata: CompletionUsage = (
                self.convert_usage_meta_data_to_openai(
                    usages=[usage_metadata] if usage_metadata else []
                )
            )
            content_text: str = convert_message_content_to_string(content)
            if not isinstance(content_text, str):
                raise TypeError(f"content_text must be str, got {type(content_text)}")
            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1" and content_text:
                logger.debug(f"Returning content: {content_text}")
            if content_text:
                chat_model_stream_response: ChatCompletionChunk = ChatCompletionChunk(
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
                yield format_chat_completion_chunk_sse(
                    chat_model_stream_response.model_dump()
                )

    async def _handle_on_chain_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
    ) -> AsyncGenerator[str, None]:
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        data = event["data"] if "data" in event else {}
        output: Dict[str, Any] | str | None = data.get("output")
        if output and isinstance(output, dict) and "usage_metadata" in output:
            completion_usage_metadata: CompletionUsage = (
                self.convert_usage_meta_data_to_openai(
                    usages=[output["usage_metadata"]]
                )
            )
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

    async def _handle_on_tool_start(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        tool_name: Optional[str] = event["name"] if "name" in event else None
        data = event["data"] if "data" in event else {}
        tool_input: Optional[Dict[str, Any]] = data.get("input")
        tool_input_display: Optional[Dict[str, Any]] = (
            tool_input.copy() if tool_input is not None else None
        )
        if tool_input_display and "auth_token" in tool_input_display:
            tool_input_display["auth_token"] = "***"
        if tool_input_display and "state" in tool_input_display:
            tool_input_display["state"] = "***"
        tool_key: str = self.make_tool_key(tool_name, tool_input)
        tool_start_times[tool_key] = time.time()
        if tool_name:
            logger.debug(f"on_tool_start: {tool_name} {tool_input_display}")
            chat_stream_response: ChatCompletionChunk = ChatCompletionChunk(
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
            yield format_chat_completion_chunk_sse(chat_stream_response.model_dump())

    async def _handle_on_tool_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        request: ChatRequest,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
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
            logger.info(f"Tool {tool_name2} completed in {elapsed:.2f} seconds.")
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
                tool_message_content: str = self.convert_message_content_into_string(
                    tool_message=tool_message
                )
                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                    logger.info(
                        f"Returning artifact: {artifact if artifact else tool_message_content}"
                    )
                token_count: int = self.token_reducer.count_tokens(
                    tool_message_content if return_raw_tool_output else str(artifact)
                )
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
                    else f"\n> {artifact}"
                    + (
                        f" [tokens: {token_count}]"
                        if logger.isEnabledFor(logging.DEBUG) > 0
                        else ""
                    )
                )
                chat_stream_response: ChatCompletionChunk = ChatCompletionChunk(
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
            yield format_chat_completion_chunk_sse(chat_stream_response.model_dump())

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
