from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict


class CacheItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
        json_encoders={ObjectId: str},  # Convert ObjectId to string for JSON
    )
    id: Optional[str]
    value: Optional[str]
