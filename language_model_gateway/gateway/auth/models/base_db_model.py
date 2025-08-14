from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BaseDbModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
    )
    id: ObjectId = Field(alias="_id")

    @field_serializer("id")
    def serialize_object_id(self, object_id: ObjectId) -> str:
        return str(object_id)
