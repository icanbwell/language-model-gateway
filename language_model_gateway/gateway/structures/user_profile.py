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

    def to_text(self) -> str:
        """
        Convert the user profile to a human-readable text format.

        :return: A string representation of the user profile.
        """
        profile_parts = [f"User ID: {self.user_id}", f"Name: {self.name}"]
        if self.age is not None:
            profile_parts.append(f"Age: {self.age}")
        if self.recent_memories:
            profile_parts.append(f"Recent Memories: {', '.join(self.recent_memories)}")
        if self.preferences:
            prefs = ", ".join(f"{k}: {v}" for k, v in self.preferences.items())
            profile_parts.append(f"Preferences: {prefs}")
        return "\n".join(profile_parts)
