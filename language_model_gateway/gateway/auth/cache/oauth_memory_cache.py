import uuid
from typing import override

from language_model_gateway.gateway.auth.cache.oauth_cache import OAuthCache


class OAuthMemoryCache(OAuthCache):
    @property
    def id(self) -> uuid.UUID:
        return self.id_

    _cache: dict[str, str] = {}

    def __init__(self) -> None:
        """Initialize the AuthCache."""
        self.id_ = uuid.uuid4()

    @override
    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        :param key: Unique identifier for the cache entry.
        """
        if key in self._cache:
            del self._cache[key]

    @override
    async def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a value from the cache.

        :param key: Unique identifier for the cache entry.
        :param default: Default value to return if the key is not found.
        :return: Retrieved value or None if not found or expired.
        """
        return self._cache.get(key) or default

    @override
    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Set a value in the cache with optional expiration.

        :param key: Unique identifier for the cache entry.
        :param value: Value to be stored.
        :param expires: Expiration time in seconds. Defaults to None (no expiration).
        """
        self._cache[key] = value
