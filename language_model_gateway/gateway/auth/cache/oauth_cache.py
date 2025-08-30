import uuid
from abc import abstractmethod, ABCMeta


class OAuthCache(metaclass=ABCMeta):
    """
    Base class for OAuthCache
    """

    @property
    @abstractmethod
    def id(self) -> uuid.UUID:
        """
        Unique identifier for the cache instance.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        :param key: Unique identifier for the cache entry.
        """
        ...

    @abstractmethod
    async def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a value from the cache.

        :param key: Unique identifier for the cache entry.
        :param default: Default value to return if the key is not found.
        :return: Retrieved value or None if not found or expired.
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Set a value in the cache with optional expiration.

        :param key: Unique identifier for the cache entry.
        :param value: Value to be stored.
        :param expires: Expiration time in seconds. Defaults to None (no expiration).
        """
        ...
