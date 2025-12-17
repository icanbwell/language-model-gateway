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

from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
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
from language_model_gateway.gateway.utilities.url_parser import UrlParser

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class LangGraphStreamingManager:
    def __init__(
        self,
        *,
        token_reducer: TokenReducer,
        file_manager_factory: FileManagerFactory,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
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
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
        try:
            event_type: str = event["event"]
            # Events defined here:
            # https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.BaseChatModel.astream_events
            match event_type:
                case "on_chat_model_start":
                    pass
                case "on_chat_model_end":
                    pass
                case "on_chain_start":
                    pass
                case "on_chain_stream":
                    pass
                case "on_chat_model_stream":
                    async for chunk in self._handle_on_chat_model_stream(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_id=request_id,
                    ):
                        yield chunk
                case "on_chain_end":
                    async for chunk in self._handle_on_chain_end(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_id=request_id,
                    ):
                        yield chunk
                case "on_tool_start":
                    async for chunk in self._handle_on_tool_start(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_id=request_id,
                        tool_start_times=tool_start_times,
                    ):
                        yield chunk
                case "on_tool_end":
                    async for chunk in self._handle_on_tool_end(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_id=request_id,
                        tool_start_times=tool_start_times,
                    ):
                        yield chunk
                case "on_tool_error":
                    async for chunk in self._handle_on_tool_error(
                        event=event,
                        chat_request_wrapper=chat_request_wrapper,
                        request_id=request_id,
                        tool_start_times=tool_start_times,
                    ):
                        yield chunk
                case _:
                    logger.debug(f"Skipped event type: {event_type}")
        except Exception as e:
            logger.error(f"Error handling langchain event: {e}")

    async def _handle_on_chat_model_stream(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_id: str,
    ) -> AsyncGenerator[str, None]:
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
                    request_id=request_id,
                    content=content_text,
                    usage_metadata=chunk.usage_metadata,
                )

    async def _handle_on_chain_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_id: str,
    ) -> AsyncGenerator[str, None]:
        # Fix mypy TypedDict .get() error by using square bracket access and key existence checks
        data = event["data"] if "data" in event else {}
        output: Dict[str, Any] | str | None = data.get("output")
        if output and isinstance(output, dict) and "usage_metadata" in output:
            yield chat_request_wrapper.create_final_sse_message(
                request_id=request_id,
                usage_metadata=output["usage_metadata"],
            )

    async def _handle_on_tool_start(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
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
            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                content=content_text,
                usage_metadata=None,
            )

    async def _handle_on_tool_end(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
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
                if structured_data_without_result.get("structured_content"):
                    structured_data_without_result["structured_content"].pop(
                        "result", None
                    )

            if artifact or return_raw_tool_output:
                tool_message_content: str = self.convert_message_content_into_string(
                    tool_message=tool_message
                )
                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                    logger.debug(
                        f"Returning artifact: {artifact if artifact else tool_message_content}"
                    )

                tool_message_content_length: int = len(tool_message_content)
                artifact_text = await self.convert_tool_artifact_to_text(
                    artifact=artifact
                )
                token_count: int = self.token_reducer.count_tokens(
                    tool_message_content if not artifact else artifact_text
                )
                file_url: Optional[str] = None
                if (
                    tool_message_content_length
                    > self.environment_variables.maximum_inline_tool_output_size
                ):
                    # Save to file and provide link
                    output_folder = os.environ.get("IMAGE_GENERATION_PATH")
                    if output_folder:
                        file_manager = self.file_manager_factory.get_file_manager(
                            folder=output_folder
                        )
                        filename = f"tool_output_{tool_name2}_{int(time.time())}.txt"
                        file_path: Optional[str] = await file_manager.save_file_async(
                            file_data=artifact_text.encode("utf-8"),
                            folder=output_folder,
                            filename=filename,
                            content_type="text/plain",
                        )
                        if file_path:
                            tool_message_content = (
                                ""  # clear the content since we're using a file
                            )
                            tool_message_content += (
                                "\n--- Structured Content (w/o result) ---\n"
                            )
                            tool_message_content += (
                                json.dumps(structured_data_without_result)
                                if structured_data_without_result
                                else ""
                            )
                            tool_message_content += "\n--- End Structured Content ---\n"
                            try:
                                file_url = UrlParser.get_url_for_file_name(filename)
                                if file_url is not None:
                                    tool_message_content += f"\n(URL: {file_url})"
                                else:
                                    tool_message_content += (
                                        "\nTool output file URL could not be generated."
                                    )
                            except KeyError:
                                tool_message_content += "\nTool output file URL could not be generated due to missing IMAGE_GENERATION_URL environment variable."
                        else:
                            tool_message_content = (
                                "Tool output too large to display inline, "
                                "and failed to save to file."
                            )
                    else:
                        tool_message_content = (
                            f"Tool output too large to display inline,"
                            f" {tool_message_content_length} > {self.environment_variables.maximum_inline_tool_output_size}"
                            " and TOOL_OUTPUT_FILE_PATH is not set."
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
                    else f"\n> {artifact}" + f" [tokens: {token_count}]"
                )
                yield chat_request_wrapper.create_sse_message(
                    request_id=request_id,
                    content=tool_progress_message,
                    usage_metadata=None,
                )
                if file_url:
                    # send a follow-up message with the file URL
                    content_text: str = (
                        f"\n\n[Click to download Tool Output]({file_url})\n\n"
                    )
                    yield chat_request_wrapper.create_sse_message(
                        request_id=request_id, content=content_text, usage_metadata=None
                    )
        else:
            logger.debug("on_tool_end: no tool message output")
            content_text = f"\n\n> Tool completed with no output.{runtime_str}\n"
            yield chat_request_wrapper.create_sse_message(
                request_id=request_id,
                content=content_text,
                usage_metadata=None,
            )

    @staticmethod
    def _format_text_resource_contents(text: str) -> str:
        """
        Helper to format TextResourceContents, extracting JSON fields if possible.
        """
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

    @staticmethod
    async def convert_tool_artifact_to_text(*, artifact: Any | None) -> str:
        try:
            if isinstance(artifact, str):
                return artifact
            if isinstance(artifact, list):
                # each entry may be an EmbeddableResource
                result = ""
                for item in artifact:
                    if hasattr(item, "resource") and hasattr(item.resource, "text"):
                        result += (
                            LangGraphStreamingManager._format_text_resource_contents(
                                item.resource.text
                            )
                        )
                return result.strip()
            # finally try to convert to str
            return str(artifact)
        except Exception as e:
            return (
                f"Could not convert artifact of type {type(artifact)} to string: {e}."
            )

    async def _handle_on_tool_error(
        self,
        *,
        event: StandardStreamEvent | CustomStreamEvent,
        chat_request_wrapper: ChatRequestWrapper,
        request_id: str,
        tool_start_times: dict[str, float],
    ) -> AsyncGenerator[str, None]:
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
            request_id=request_id,
            content=content_text,
            usage_metadata=None,
        )

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
    def safe_json(string: str) -> Any:
        try:
            return json.loads(string)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def convert_message_content_into_string(*, tool_message: ToolMessage) -> str:
        if isinstance(tool_message.content, str):
            # the content is str then just return it
            # see if this is a json object embedded in text
            return LangGraphStreamingManager._format_text_resource_contents(
                text=tool_message.content
            )

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

    @staticmethod
    def get_structured_content_from_tool_message(
        *, tool_message: ToolMessage
    ) -> dict[str, Any] | None:
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
