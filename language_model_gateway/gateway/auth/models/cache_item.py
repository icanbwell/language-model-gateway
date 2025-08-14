from typing import Optional

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel


class CacheItem(BaseDbModel):
    """
    Represents a cache item with a key and value.
    This model is used to store key-value pairs in the cache.
    """

    key: Optional[str]
    """The key for the cache item, which is used to identify the item in the cache."""
    value: Optional[str]
    """The value associated with the key in the cache item, which can be any string data."""
