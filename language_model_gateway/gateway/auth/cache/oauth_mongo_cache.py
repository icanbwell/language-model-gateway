import os

from language_model_gateway.gateway.auth.models.CacheItem import CacheItem
from language_model_gateway.gateway.auth.mongo.mongo_repository import (
    AsyncMongoRepository,
)


class OAuthMongoCache:
    def __init__(self) -> None:
        """Initialize the AuthCache."""
        connection_string = os.getenv("MONGO_URL")
        assert connection_string, "MONGO_URL environment variable is not set."
        database_name = os.getenv("MONGO_DB_NAME")
        assert database_name, "MONGO_DB_NAME environment variable is not set."
        collection_name = os.getenv("MONGO_DB_COLLECTION_NAME")
        assert collection_name, (
            "MONGO_DB_COLLECTION_NAME environment variable is not set."
        )

        self.repository: AsyncMongoRepository[CacheItem] = AsyncMongoRepository(
            connection_string=connection_string,
            database_name=database_name,
        )
        self.collection_name = collection_name

    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        :param key: Unique identifier for the cache entry.
        """
        # check if the key exists in the repository
        cache_item: CacheItem | None = await self.repository.find_by_id(
            collection_name=self.collection_name,
            model_class=CacheItem,
            document_id=key,
        )
        if cache_item is not None:
            # delete the cache item if it exists
            await self.repository.delete_by_id(
                collection_name=self.collection_name,
                document_id=key,
            )

    async def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a value from the cache.

        :param key: Unique identifier for the cache entry.
        :param default: Default value to return if the key is not found.
        :return: Retrieved value or None if not found or expired.
        """
        cache_item: CacheItem | None = await self.repository.find_by_id(
            collection_name=self.collection_name,
            model_class=CacheItem,
            document_id=key,
        )
        return cache_item.value if cache_item is not None else default

    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Set a value in the cache with optional expiration.

        :param key: Unique identifier for the cache entry.
        :param value: Value to be stored.
        :param expires: Expiration time in seconds. Defaults to None (no expiration).
        """
        cache_item = CacheItem(id=key, value=value)
        await self.repository.save(
            collection_name=self.collection_name,
            model=cache_item,
        )
