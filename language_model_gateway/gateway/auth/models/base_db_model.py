from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BaseDbModel(BaseModel):
    """
    Base model for all database models in the application.
    This model provides a common structure for all database entities, including an
    ObjectId field for the primary key and a serializer for the ObjectId to string conversion.
    It uses Pydantic's ConfigDict to allow population by name and to permit arbitrary types.
    The `id` field is aliased to `_id` to match MongoDB's default behavior for primary keys.
    """

    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
    )
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")

    @field_serializer("id")
    def serialize_object_id(self, object_id: ObjectId) -> str:
        """
        Serialize the ObjectId to a string for JSON representation.
        This method is used to convert the ObjectId to a string when the model is serialized,
        allowing it to be easily represented in JSON or other formats.
        """
        return str(object_id)
