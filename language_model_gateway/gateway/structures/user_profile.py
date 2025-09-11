from typing import Dict, Any

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str = Field(description="Unique identifier for the user")
    name: str = Field(description="Name of the current user")
    age: int | None = Field(default=None, description="Optional age of the user")
    recent_memories: list[str] = Field(
        default=[], description="list of recent memories or interactions with the user"
    )
    preferences: Dict[str, Any] | None = Field(
        default=None, description="Optional dictionary of user preferences"
    )
