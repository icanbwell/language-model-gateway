import json
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union
import inspect

import redis
from pydantic import BaseModel

from language_model_gateway.gateway.auth.repository.base_db_model import BaseDbModel

T = TypeVar("T", bound=BaseDbModel)


class RedisConfig:
    """
    Configuration class for Redis connections with comprehensive settings.
    """

    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0
    PASSWORD: Optional[str] = None
    SOCKET_TIMEOUT: Optional[float] = 5.0
    SOCKET_CONNECT_TIMEOUT: Optional[float] = 5.0
    RETRY_ON_TIMEOUT: bool = True
    MAX_CONNECTIONS: int = 10


class PydanticRedisRepository(Generic[T]):
    """
    Comprehensive Redis repository for Pydantic models with advanced features.
    """

    def __init__(
        self,
        model_class: Type[T],
        prefix: Optional[str] = None,
        redis_config: RedisConfig = RedisConfig(),
    ):
        """
        Initialize Redis repository with advanced configuration.

        Args:
            model_class (Type[T]): Pydantic model class
            prefix (Optional[str]): Key prefix for namespacing
            redis_config (RedisConfig): Redis connection configuration
        """
        self._model_class = model_class
        self._prefix = prefix or model_class.__name__.lower()

        # Create Redis connection pool
        self._redis_pool = redis.ConnectionPool(
            host=redis_config.HOST,
            port=redis_config.PORT,
            db=redis_config.DB,
            password=redis_config.PASSWORD,
            socket_timeout=redis_config.SOCKET_TIMEOUT,
            socket_connect_timeout=redis_config.SOCKET_CONNECT_TIMEOUT,
            retry_on_timeout=redis_config.RETRY_ON_TIMEOUT,
            max_connections=redis_config.MAX_CONNECTIONS,
        )

        # Create Redis client
        self._redis = redis.Redis(
            connection_pool=self._redis_pool, decode_responses=True
        )

    def _generate_key(self, key_id: Optional[str] = None) -> str:
        """
        Generate a unique Redis key with namespacing.

        Args:
            key_id (Optional[str]): Optional specific ID

        Returns:
            str: Formatted Redis key
        """
        return f"{self._prefix}:{key_id or str(uuid.uuid4())}"

    def _serialize_model(self, model: T) -> str:
        """
        Serialize Pydantic model to JSON string with advanced handling.

        Args:
            model (T): Pydantic model to serialize

        Returns:
            str: JSON string representation
        """
        return model.model_dump_json(
            exclude_unset=True,  # Exclude fields not explicitly set
            by_alias=True,  # Use field aliases
        )

    def _deserialize_model(self, json_str: str) -> T:
        """
        Deserialize JSON string to Pydantic model with robust parsing.

        Args:
            json_str (str): JSON string to deserialize

        Returns:
            T: Pydantic model instance
        """
        return self._model_class.model_validate_json(json_str)

    def save(
        self,
        model: T,
        key_id: Optional[str] = None,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> str:
        """
        Save Pydantic model to Redis with advanced options.

        Args:
            model (T): Pydantic model to save
            key_id (Optional[str]): Specific key ID
            expire (Optional[Union[int, timedelta]]): Expiration time

        Returns:
            str: Redis key used for storage
        """
        # Generate or use provided key
        key = self._generate_key(key_id)

        # Serialize model
        serialized_model = self._serialize_model(model)

        # Save to Redis with transaction support
        with self._redis.pipeline() as pipe:
            pipe.set(key, serialized_model)

            # Set expiration if provided
            if expire is not None:
                pipe.expire(key, expire)

            pipe.execute()

        return key

    async def get(self, key_id: str) -> Optional[T]:
        """
        Retrieve model by key ID with robust error handling.

        Args:
            key_id (str): Redis key ID

        Returns:
            Optional[T]: Retrieved Pydantic model or None
        """
        key = f"{self._prefix}:{key_id}"
        try:
            serialized_model = self._redis.get(key)
            if inspect.isawaitable(serialized_model):
                serialized_model = await serialized_model
            if not serialized_model:
                return None
            return self._deserialize_model(serialized_model)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Deserialization error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error retrieving {key}: {e}")
            return None

    async def update(
        self,
        key_id: str,
        model: T,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Update an existing model with partial update support.

        Args:
            key_id (str): Redis key ID
            model (T): Updated Pydantic model
            expire (Optional[Union[int, timedelta]]): Expiration time

        Returns:
            bool: True if update was successful
        """
        key = f"{self._prefix}:{key_id}"
        exists = self._redis.exists(key)
        if inspect.isawaitable(exists):
            exists = await exists
        if not exists:
            return False
        try:
            serialized_model = self._serialize_model(model)
            result = self._redis.set(key, serialized_model)
            if inspect.isawaitable(result):
                result = await result
            if expire is not None:
                expire_result = self._redis.expire(key, expire)
                if inspect.isawaitable(expire_result):
                    await expire_result
            return True
        except Exception as e:
            print(f"Error updating key {key}: {e}")
            return False

    async def find_by_pattern(self, pattern: str, limit: int = 100) -> list[T]:
        """
        Find models by key pattern with advanced filtering.

        Args:
            pattern (str): Redis key pattern
            limit (int): Maximum number of results

        Returns:
            list[T]: List of matching Pydantic models
        """
        full_pattern = f"{self._prefix}:{pattern}"
        matching_keys = self._redis.keys(full_pattern)
        if inspect.isawaitable(matching_keys):
            matching_keys = await matching_keys
        matching_keys = matching_keys[:limit]
        models = []
        for key in matching_keys:
            try:
                serialized_model = self._redis.get(key)
                if inspect.isawaitable(serialized_model):
                    serialized_model = await serialized_model
                if serialized_model:
                    models.append(self._deserialize_model(serialized_model))
            except Exception as e:
                print(f"Error processing key {key}: {e}")

        return models

    def set_hash(
        self,
        key_id: str,
        data: Dict[str, Any],
        expire: Optional[Union[int, timedelta]] = None,
    ) -> str:
        """
        Store data as a Redis Hash with advanced options.

        Args:
            key_id (str): Unique key identifier
            data (Dict[str, Any]): Dictionary of field-value pairs
            expire (Optional[Union[int, timedelta]]): Expiration time

        Returns:
            str: Full Redis key
        """
        # Construct full key
        key = f"{self._prefix}:hash:{key_id}"

        # Convert values to strings
        hash_data = {
            str(k): json.dumps(v) if not isinstance(v, str) else v
            for k, v in data.items()
        }

        # Use transaction for atomic operation
        with self._redis.pipeline() as pipe:
            pipe.hset(key, mapping=hash_data)

            # Set expiration if provided
            if expire is not None:
                pipe.expire(key, expire)

            pipe.execute()

        return key

    async def get_hash(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from a Redis Hash with type restoration.

        Args:
            key_id (str): Unique key identifier

        Returns:
            Optional[Dict[str, Any]]: Retrieved hash data
        """
        # Construct full key
        key = f"{self._prefix}:hash:{key_id}"

        # Retrieve hash data
        hash_data = self._redis.hgetall(key)
        if inspect.isawaitable(hash_data):
            hash_data = await hash_data
        if not hash_data:
            return None

        # Restore original types
        restored_data = {}
        for k, v in hash_data.items():
            try:
                restored_data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                restored_data[k] = v

        return restored_data
