import typing
from typing import (
    Optional,
    Any,
    Sequence,
    Callable,
    AsyncIterator,
    Iterator,
    override,
)

from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatResult, ChatGenerationChunk, ChatGeneration
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from tests.gateway.mocks.mock_ai_message_protocol import MockAiMessageProtocol
from language_model_gateway.gateway.utilities.openai.responses_api_converter import (
    convert_responses_api_to_messages,
)


class MockResponsesModel(BaseChatModel):
    fn_get_response: MockAiMessageProtocol

    @override
    @property
    def _llm_type(self) -> str:
        return "mock-responses"

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Simulate a Responses API response
        response_str = self.fn_get_response(messages=messages)
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_str}],
                }
            ]
        }
        result_messages = convert_responses_api_to_messages(response)
        ai_message = next(
            (m for m in result_messages if isinstance(m, AIMessage)),
            AIMessage(content=""),
        )
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @override
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_str = self.fn_get_response(messages=messages)
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_str}],
                }
            ]
        }
        result_messages = convert_responses_api_to_messages(response)
        ai_message = next(
            (m for m in result_messages if isinstance(m, AIMessage)),
            AIMessage(content=""),
        )
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @override
    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        response_str = self.fn_get_response(messages=messages)
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_str}],
                }
            ]
        }
        result_messages = convert_responses_api_to_messages(response)
        ai_message = next(
            (m for m in result_messages if isinstance(m, AIMessage)),
            AIMessage(content=""),
        )
        return iter(
            [ChatGenerationChunk(message=AIMessageChunk(content=ai_message.content))]
        )

    @override
    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        response_str = self.fn_get_response(messages=messages)
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_str}],
                }
            ]
        }
        result_messages = convert_responses_api_to_messages(response)
        ai_message = next(
            (m for m in result_messages if isinstance(m, AIMessage)),
            AIMessage(content=""),
        )
        if isinstance(ai_message.content, str):
            words = ai_message.content.split()
            for word in words:
                yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))
        else:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=str(ai_message.content))
            )

    @override
    def bind_tools(
        self,
        tools: Sequence[typing.Dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self
