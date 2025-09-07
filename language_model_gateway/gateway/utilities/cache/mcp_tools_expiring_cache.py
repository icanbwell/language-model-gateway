import asyncio
import logging
import time
from typing import Optional, Dict, List, override
from uuid import uuid4, UUID

from mcp import Tool

from language_model_gateway.gateway.utilities.cache.expiring_cache import ExpiringCache
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class McpToolsMetadataExpiringCache(ExpiringCache[Dict[str, List[Tool]]]):
    """
    Expiring cache for MCP tools metadata.

    This cache stores metadata about tools used in MCP (Model Configuration Protocol)
    and expires after a specified time-to-live (TTL) period.
    It is designed to be used in asynchronous environments and supports thread-safe operations.
    The cache can be initialized with an optional initial value and will automatically
    expire after the specified TTL in seconds.
    """

    _cache: Optional[Dict[str, List[Tool]]] = None
    """ Cache for MCP tools metadata, stored as a dictionary mapping tool names to lists of Tool objects. """
    _cache_timestamp: Optional[float] = None
    """ Timestamp when the cache was last updated, used to determine cache validity. """
    _lock: asyncio.Lock = asyncio.Lock()
    """ Asynchronous lock to ensure thread-safe access to the cache. """

    def __init__(
        self, *, ttl_seconds: float, init_value: Optional[Dict[str, List[Tool]]] = None
    ) -> None:
        """
        Initialize the expiring cache for MCP tools metadata.
        Args:
            ttl_seconds (float): Time-to-live for the cache in seconds. After this period,
                                 the cache will be considered invalid.
            init_value (Optional[Dict[str, List[Tool]]]): Optional initial value to populate the cache.
                                                          If not provided, the cache starts empty.

        """
        self._ttl: float = ttl_seconds
        self._identifier: UUID = uuid4()
        if init_value is not None:
            self._cache = init_value
            self._cache_timestamp = time.time()

    @override
    def is_valid(self) -> bool:
        """
        Check if the cache is still valid based on the TTL.
        Returns:
            bool: True if the cache is valid (i.e., not expired), False otherwise.
        """
        if self._cache is None or self._cache_timestamp is None:
            return False
        current_time: float = time.time()
        cache_is_valid: bool = current_time - self._cache_timestamp < self._ttl
        logger.debug(
            f"ExpiringCache with id: {self._identifier} cache is valid: {cache_is_valid}. "
            f"current time({current_time}) - cache_timestamp({self._cache_timestamp}) < ttl ({self._ttl})"
        )
        return cache_is_valid

    @override
    async def get(self) -> Optional[Dict[str, List[Tool]]]:
        """
        Retrieve the current cache value if it is valid.
        Returns:
        Optional[Dict[str, List[Tool]]]: The cached metadata if valid, None otherwise.
        """
        if self.is_valid():
            return self._cache
        return None

    @override
    async def set(self, value: Dict[str, List[Tool]]) -> None:
        """
        Set the cache to a new value and update the cache timestamp.

        Args:
            value (Dict[str, List[Tool]]): The new metadata to store in the cache

        """
        async with self._lock:
            self._cache = value
            self._cache_timestamp = time.time()
            logger.info(
                f"ExpiringCache with id: {self._identifier} set cache with timestamp: {self._cache_timestamp}"
            )

    @override
    async def create(
        self, *, init_value: Optional[Dict[str, List[Tool]]] = None
    ) -> Dict[str, List[Tool]] | None:
        """
        Create a new cache with an optional initial value.

        Args:
            init_value (Optional[Dict[str, List[Tool]]]): Optional initial value to populate
            the cache. If not provided, the cache starts empty.
        Returns:
            Optional[Dict[str, List[Tool]]]: The newly created cache, which may be empty if no initial value is provided.
        """
        async with self._lock:
            self._cache = init_value if init_value is not None else {}
            self._cache_timestamp = time.time()
            logger.info(f"ExpiringCache with id: {self._identifier} created cache")
            return self._cache

    @override
    async def clear(self) -> None:
        """
        Clear the cache by setting it to None and resetting the timestamp.
        This method is thread-safe and ensures that the cache is emptied.

        """
        async with self._lock:
            self._cache = None
            self._cache_timestamp = None
            logger.info(f"ExpiringCache with id: {self._identifier} cleared cache")
