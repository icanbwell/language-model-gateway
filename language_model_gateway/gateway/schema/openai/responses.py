from typing import Optional, Union, Any

from openai.types.responses import ResponseInputParam
from pydantic import BaseModel, Field, ConfigDict


class ResponsesRequest(BaseModel):
    """Request model for OpenAI Responses API."""

    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )

    # Required parameters
    model: str = Field(..., description="The model to use for generating the response.")
    input: Union[str, ResponseInputParam] = Field(
        ..., description="The input text or data to generate a response for."
    )

    # Optional parameters
    stream: bool = False
    instructions: Optional[str] = None
    previous_response_id: Optional[str] = None
    store: Optional[bool] = False

    # Generation parameters
    temperature: Optional[float] = Field(None, ge=0, le=2)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    max_output_tokens: Optional[int] = Field(None, gt=0)

    # Additional parameters
    truncation: Optional[str] = None
    service_tier: Optional[str] = None
    user: Optional[str] = None
    include: Optional[list[str]] = None

    # Tools (not fully implemented yet)
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None

    # LangGraph context
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
