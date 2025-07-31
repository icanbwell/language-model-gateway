from abc import ABC, abstractmethod
from typing import Optional


class ExpiringCache[T](ABC):
    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    async def get(self) -> Optional[T]:
        pass

    @abstractmethod
    async def set(self, value: T) -> None:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass
