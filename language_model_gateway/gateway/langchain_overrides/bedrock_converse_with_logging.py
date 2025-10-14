import logging
import warnings
from typing import (
    Any,
    Iterator,
    List,
    Optional,
)

from langchain_aws import ChatBedrockConverse
from langchain_aws.chat_models.bedrock_converse import (
    _messages_to_bedrock,
    _snake_to_camel_keys,
    _has_tool_use_or_result_blocks,
    _convert_tool_blocks_to_text,
    _parse_stream_event,
)
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.outputs import ChatGenerationChunk

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ChatBedrockException(Exception):
    """Custom exception for ChatBedrock errors."""

    pass


class ChatBedrockConverseWithLogging(ChatBedrockConverse):
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        system: list[dict[str, Any]]
        bedrock_messages: list[dict[str, Any]]
        if self.raw_blocks is not None:
            logger.debug(f"Using raw blocks: {self.raw_blocks}")
            bedrock_messages, system = self.raw_blocks, []
        else:
            bedrock_messages, system = _messages_to_bedrock(messages)
            if self.guard_last_turn_only:
                logger.debug("Applying selective guardrail to only the last turn")
                self._apply_guard_last_turn_only(bedrock_messages)

        params = self._converse_params(
            stop=stop,
            **_snake_to_camel_keys(
                kwargs, excluded_keys={"inputSchema", "properties", "thinking"}
            ),
        )

        # Check for tool blocks without toolConfig and handle conversion
        if params.get("toolConfig") is None and _has_tool_use_or_result_blocks(
            bedrock_messages
        ):
            logger.warning(
                "Tool messages (toolUse/toolResult) detected without toolConfig. "
                "Converting tool blocks to text format to avoid ValidationException."
            )
            warnings.warn(
                "Tool messages were passed without toolConfig, converting to text format",
                RuntimeWarning,
            )

            bedrock_messages = _convert_tool_blocks_to_text(bedrock_messages)
            logger.debug(f"converted input messages: {bedrock_messages}")

        bedrock_messages_text = "\n".join(str(msg) for msg in bedrock_messages)
        logger.debug(
            f"Sending messages to Bedrock model {self.model_id}\nMessages:\n{bedrock_messages_text}"
        )
        try:
            response = self.client.converse_stream(
                messages=bedrock_messages, system=system, **params
            )
            added_model_name = False
            for event in response["stream"]:
                if message_chunk := _parse_stream_event(event):
                    if (
                        hasattr(message_chunk, "usage_metadata")
                        and message_chunk.usage_metadata
                        and not added_model_name
                    ):
                        message_chunk.response_metadata["model_name"] = self.model_id
                        if metadata := response.get("ResponseMetadata"):
                            message_chunk.response_metadata["ResponseMetadata"] = (
                                metadata
                            )
                        added_model_name = True
                    generation_chunk = ChatGenerationChunk(message=message_chunk)
                    if run_manager:
                        run_manager.on_llm_new_token(
                            generation_chunk.text, chunk=generation_chunk
                        )
                    yield generation_chunk
        except Exception as e:
            logger.exception(
                f"Error during Bedrock converse_stream: {e} with messages: {bedrock_messages_text}"
            )
            raise ChatBedrockException(
                f"Bedrock converse_stream failed: {e}\nMessages:\n{bedrock_messages_text}"
            ) from e
