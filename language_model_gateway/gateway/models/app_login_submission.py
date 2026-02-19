from pydantic import BaseModel, Field


class CredentialSubmission(BaseModel):
    """Validated payload produced from the credential capture form."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
