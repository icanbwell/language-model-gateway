from abc import ABC, abstractmethod
from typing import Optional


class ExpiringCache[T](ABC):
    """
    Abstract base class for an expiring cache.
    This class defines the interface for an expiring cache that can store and manage
    values of type T with an expiration mechanism.
    It provides methods to check validity, get, set, clear, and create cache entries.
    Attributes:
        T (type): The type of value stored in the cache.
    """

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if the cache is valid based on its expiration criteria.
        Returns:
            bool: True if the cache is valid (i.e., not expired), False otherwise.
        """
        pass

    @abstractmethod
    async def get(self) -> Optional[T]:
        """
        Retrieve the current cache value if it is valid.
        Returns:
            Optional[T]: The cached value if valid, None otherwise.
        """
        pass

    @abstractmethod
    async def set(self, value: T) -> None:
        """
        Set the cache to a new value and update the cache timestamp.
        Args:
            value (T): The new value to store in the cache.
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clear the cache, removing any stored value and resetting the timestamp.
        """
        pass

    @abstractmethod
    async def create(self, *, init_value: Optional[T] = None) -> Optional[T]:
        """
        Create a new cache with an optional initial value.
        Args:
            init_value (Optional[T]): An optional initial value to set in the cache.
        Returns:
            Optional[T]: The initial value if provided, None otherwise.
        """
        pass
