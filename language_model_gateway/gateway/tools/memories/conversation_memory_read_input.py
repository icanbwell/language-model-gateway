import typing
from typing import Dict, Any
from pydantic import BaseModel, Field


class ConversationMemoryReadInput(BaseModel):
    all_memories: typing.Optional[bool] = Field(
        default=False,
        description="If true, retrieve all memories for the user. ",
    )
    query: typing.Optional[str] = Field(
        default=None,
        description="Query string to search for relevant memories. ",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of memories to return. ",
    )
    offset: int = Field(
        default=0,
        description="Number of memories to skip before starting to collect the result set. ",
    )
    filter_: typing.Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filter to apply to the memories. ",
    )
