from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class User(BaseModel):
    """
    User model with MongoDB-specific configuration.
    """

    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
        json_encoders={ObjectId: str},  # Convert ObjectId to string for JSON
    )

    id: Optional[str] = Field(None, alias="_id")
    username: str
    email: str
    age: int
    active: bool = True
