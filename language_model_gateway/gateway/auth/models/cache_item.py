from typing import Optional

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel


class CacheItem(BaseDbModel):
    key: Optional[str]
    value: Optional[str]
