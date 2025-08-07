from fastapi import FastAPI


class OAuthCache:
    _cache: dict[str, str] = {}

    def __init__(self, app: FastAPI) -> None:
        """Initialize the AuthCache."""
        self.app = app

    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        :param key: Unique identifier for the cache entry.
        """
        if key in self._cache:
            del self._cache[key]

    async def get(self, key: str, default: str | None) -> str | None:
        """
        Retrieve a value from the cache.

        :param key: Unique identifier for the cache entry.
        :param default: Default value to return if the key is not found.
        :return: Retrieved value or None if not found or expired.
        """
        return self._cache.get(key) or default

    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Set a value in the cache with optional expiration.

        :param key: Unique identifier for the cache entry.
        :param value: Value to be stored.
        :param expires: Expiration time in seconds. Defaults to None (no expiration).
        """
        self._cache[key] = value
