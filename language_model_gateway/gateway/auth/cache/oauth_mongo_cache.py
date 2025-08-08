import logging
import os
import uuid
from typing import override

from bson import ObjectId

from language_model_gateway.gateway.auth.cache.oauth_cache import OAuthCache
from language_model_gateway.gateway.auth.models.CacheItem import CacheItem
from language_model_gateway.gateway.auth.mongo.mongo_repository import (
    AsyncMongoRepository,
)

logger = logging.getLogger(__name__)


class OAuthMongoCache(OAuthCache):
    def __init__(self) -> None:
        """Initialize the AuthCache."""
        self.id_ = uuid.uuid4()
        connection_string = os.getenv("MONGO_URL")
        assert connection_string, "MONGO_URL environment variable is not set."
        database_name = os.getenv("MONGO_DB_NAME")
        assert database_name, "MONGO_DB_NAME environment variable is not set."
        collection_name = os.getenv("MONGO_DB_AUTH_CACHE_COLLECTION_NAME")
        assert collection_name, (
            "MONGO_DB_AUTH_CACHE_COLLECTION_NAME environment variable is not set."
        )

        self.repository: AsyncMongoRepository[CacheItem] = AsyncMongoRepository(
            connection_string=connection_string,
            database_name=database_name,
        )
        self.collection_name = collection_name

    @property
    def id(self) -> uuid.UUID:
        return self.id_

    @override
    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        :param key: Unique identifier for the cache entry.
        """
        # check if the key exists in the repository
        cache_item: CacheItem | None = await self.repository.find_by_fields(
            collection_name=self.collection_name,
            model_class=CacheItem,
            fields={
                "key": key,
            },
        )
        if cache_item is not None and cache_item.id:
            # delete the cache item if it exists
            await self.repository.delete_by_id(
                collection_name=self.collection_name,
                document_id=cache_item.id,
            )

    @override
    async def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a value from the cache.

        :param key: Unique identifier for the cache entry.
        :param default: Default value to return if the key is not found.
        :return: Retrieved value or None if not found or expired.
        """
        cache_item: CacheItem | None = await self.repository.find_by_fields(
            collection_name=self.collection_name,
            model_class=CacheItem,
            fields={
                "key": key,
            },
        )
        return cache_item.value if cache_item is not None else default

    @override
    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Set a value in the cache with optional expiration.

        :param key: Unique identifier for the cache entry.
        :param value: Value to be stored.
        :param expires: Expiration time in seconds. Defaults to None (no expiration).
        """
        # first see if the key already exists
        existing_cache_item: CacheItem | None = await self.repository.find_by_fields(
            collection_name=self.collection_name,
            model_class=CacheItem,
            fields={
                "key": key,
            },
        )
        if existing_cache_item is not None:
            # if it exists, update the value
            existing_cache_item.value = value
            new_object_id: ObjectId = await self.repository.save(
                collection_name=self.collection_name,
                model=existing_cache_item,
            )
            logger.debug(
                f"Cache item updated with ID: {new_object_id} for key: {key} with value: {value}"
            )
        else:
            cache_item = CacheItem(_id=ObjectId(), key=key, value=value)
            new_object_id = await self.repository.save(
                collection_name=self.collection_name,
                model=cache_item,
            )
            logger.debug(
                f"New cache item created with ID: {new_object_id}: {cache_item}"
            )
