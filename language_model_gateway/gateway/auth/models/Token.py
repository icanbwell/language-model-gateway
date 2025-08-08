from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Allow population by alias
        arbitrary_types_allowed=True,  # Allow non-Pydantic types
    )
    id: ObjectId = Field(alias="_id")
    name: str = Field(alias="name")
    email: str = Field(alias="email")
    url: Optional[str] = Field(None)
    access_token: Optional[str] = Field(None)
    id_token: Optional[str] = Field(None)
    expires_at: Optional[str] = Field(None)  # ISO format string for expiration time
    created_at: Optional[str] = Field(None)  # ISO format string for creation time
