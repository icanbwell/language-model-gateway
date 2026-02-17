from pydantic import BaseModel, Field


class TokenSubmission(BaseModel):
    """Validated payload produced from the token capture form."""

    token: str = Field(min_length=1, max_length=4096)
