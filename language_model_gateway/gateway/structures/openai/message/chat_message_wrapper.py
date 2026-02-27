import abc
from abc import abstractmethod
from typing import Literal

from langchain_core.messages import AnyMessage
from openai.types.chat import ChatCompletionMessageParam
from openai.types.responses.response_input_param import ResponseInputItemParam


class ChatMessageWrapper(abc.ABC):
    """
    This is the abstract base class for ChatCompletionMessageWrapper and ResponsesMessageWrapper.
    It provides a unified interface so the code can use either ChatCompletionMessageParam or ResponseInputItemParam.

    """

    """ Whether the message is a system message.  This is used for tools that need to treat system messages differently, such as a tool that extracts a JSON object from the message content and needs to ignore system messages."""

    @property
    @abstractmethod
    def system_message(self) -> bool: ...

    """ The content of the message.  This is used for tools that need to read the content of the message, such as a tool that extracts a JSON object from the message content."""

    @property
    @abstractmethod
    def content(self) -> str | None: ...

    """ Convert the message wrapper to a LangChain BaseMessage.  This is used for tools that need to convert the message to a LangChain message to use with LangChain tools."""

    @abstractmethod
    def to_langchain_message(self) -> AnyMessage: ...

    """ Convert the message wrapper back to a ChatCompletionMessageParam or ResponseInputItemParam, depending on the implementation.  This is used for tools that need to send messages back to the model in the same format as the original messages."""

    @abstractmethod
    def to_chat_completion_message(self) -> ChatCompletionMessageParam: ...

    """Convert the message wrapper to a dictionary format that can be used with the Responses API.  This is used for tools that need to convert the message to a format that can be sent to the Responses API."""

    @abstractmethod
    def to_responses_api_message(self) -> ResponseInputItemParam: ...

    @property
    @abstractmethod
    def role(self) -> Literal["system", "user", "assistant"] | None: ...
