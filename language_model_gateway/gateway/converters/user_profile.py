from typing import Dict, Any

from pydantic import BaseModel


class UserProfile(BaseModel):
    name: str
    age: int | None = None
    recent_memories: list[str] = []
    preferences: Dict[str, Any] | None = None
