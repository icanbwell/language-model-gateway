from typing import Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class UserProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
    user_id: str = Field(description="Unique identifier for the user")
    name: str | None = Field(default=None, description="Name of the current user")
    email: str | None = Field(default=None, description="Email address of the user")
    age: int | None = Field(default=None, description="Optional age of the user")
    preferences: Dict[str, Any] | None = Field(
        default=None, description="Optional dictionary of user preferences"
    )

    def to_text(self) -> str:
        """
        Convert the user profile to a human-readable text format.

        :return: A string representation of the user profile.
        """
        profile_parts = [f"User ID: {self.user_id}"]
        if self.name:
            profile_parts.append(f"Name: {self.name}")
        if self.email:
            profile_parts.append(f"Email: {self.email}")
        if self.age is not None:
            profile_parts.append(f"Age: {self.age}")
        if self.preferences:
            prefs = ", ".join(f"{k}: {v}" for k, v in self.preferences.items())
            profile_parts.append(f"Preferences: {prefs}")
        return "\n".join(profile_parts)
