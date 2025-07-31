import asyncio
import logging
import time
from typing import Optional, Dict, List
from uuid import uuid4, UUID

from mcp import Tool

from language_model_gateway.gateway.utilities.cache.expiring_cache import ExpiringCache

logger = logging.getLogger(__name__)


class McpToolsMetadataExpiringCache(ExpiringCache[Dict[str, List[Tool]]]):
    _cache: Optional[Dict[str, List[Tool]]] = None
    _cache_timestamp: Optional[float] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(
        self, *, ttl_seconds: float, init_value: Optional[Dict[str, List[Tool]]] = None
    ) -> None:
        self._ttl: float = ttl_seconds
        self._identifier: UUID = uuid4()
        if init_value is not None:
            self._cache = init_value
            self._cache_timestamp = time.time()

    def is_valid(self) -> bool:
        if self._cache is None or self._cache_timestamp is None:
            return False
        current_time: float = time.time()
        cache_is_valid: bool = current_time - self._cache_timestamp < self._ttl
        logger.debug(
            f"ExpiringCache with id: {self._identifier} cache is valid: {cache_is_valid}. "
            f"current time({current_time}) - cache_timestamp({self._cache_timestamp}) < ttl ({self._ttl})"
        )
        return cache_is_valid

    async def get(self) -> Optional[Dict[str, List[Tool]]]:
        if self.is_valid():
            return self._cache
        return None

    async def set(self, value: Dict[str, List[Tool]]) -> None:
        async with self._lock:
            self._cache = value
            self._cache_timestamp = time.time()
            logger.info(
                f"ExpiringCache with id: {self._identifier} set cache with timestamp: {self._cache_timestamp}"
            )

    async def clear(self) -> None:
        async with self._lock:
            self._cache = None
            self._cache_timestamp = None
            logger.info(f"ExpiringCache with id: {self._identifier} cleared cache")
