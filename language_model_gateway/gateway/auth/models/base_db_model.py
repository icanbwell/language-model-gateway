from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class BaseDbModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
        extra="forbid",  # Prevents any additional properties
    )
    id: ObjectId = Field(alias="_id")
