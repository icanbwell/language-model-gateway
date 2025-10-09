import abc
from abc import abstractmethod

from langchain_core.messages import BaseMessage


class ChatMessageWrapper(abc.ABC):
    """
    This is the abstract base class for ChatCompletionMessageWrapper and ResponsesMessageWrapper.
    It provides a unified interface so the code can use either ChatCompletionMessageParam or ResponseInputItemParam.

    """

    @abstractmethod
    @property
    def system_message(self) -> bool: ...

    @abstractmethod
    @property
    def content(self) -> str | None: ...

    @abstractmethod
    def to_langchain_message(self) -> BaseMessage: ...
