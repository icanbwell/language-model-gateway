from pydantic import BaseModel, Field, ConfigDict


class ConversationMemory(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
    user_id: str = Field(description="Unique identifier for the user")
    conversation_id: str = Field(description="Unique identifier for the conversation")
    memory_id: str | None = Field(
        default=None, description="Unique identifier for the memory entry"
    )
    name: str = Field(description="Name of the current user")
    recent_memories: list[str] = Field(
        default=[], description="list of recent memories or interactions with the user"
    )
