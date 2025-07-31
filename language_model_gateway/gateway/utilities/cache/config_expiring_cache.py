import asyncio
import logging
import time
from typing import Optional, List
from uuid import uuid4, UUID

from language_model_gateway.configs.config_schema import ChatModelConfig

logger = logging.getLogger(__name__)


class ConfigExpiringCache:
    _cache: Optional[List[ChatModelConfig]] = None
    _cache_timestamp: Optional[float] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(
        self, *, ttl_seconds: float, init_value: Optional[List[ChatModelConfig]] = None
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

    async def get(self) -> Optional[List[ChatModelConfig]]:
        if self.is_valid():
            return self._cache
        return None

    async def set(self, value: List[ChatModelConfig]) -> None:
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
