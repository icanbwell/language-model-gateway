import typing
from typing import (
    Optional,
    Any,
    Sequence,
    Callable,
    AsyncIterator,
    List,
    Iterator,
    override,
)

from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGenerationChunk, ChatGeneration
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from tests.gateway.mocks.mock_ai_message_protocol import MockAiMessageProtocol


class MockChatModel(BaseChatModel):
    fn_get_response: MockAiMessageProtocol

    @override
    @property
    def _llm_type(self) -> str:
        return "mock"

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content: str = self.fn_get_response(messages=messages)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))]
        )

    @override
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content: str = self.fn_get_response(messages=messages)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))]
        )

    @override
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        content: str = self.fn_get_response(messages=messages)
        return iter([ChatGenerationChunk(message=AIMessageChunk(content=content))])

    @override
    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        content: str = self.fn_get_response(messages=messages)

        # Split content into words to simulate streaming
        words = content.split()

        for i, word in enumerate(words):
            yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))

    @override
    def bind_tools(
        self,
        tools: Sequence[
            typing.Dict[str, Any] | type | Callable[..., Any] | BaseTool  # noqa: UP006
        ],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self
