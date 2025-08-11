from typing import Optional

from pydantic import Field

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel


class TokenItem(BaseDbModel):
    name: str = Field(alias="name")
    email: str = Field(alias="email")
    url: Optional[str] = Field(None)
    access_token: Optional[str] = Field(None)
    id_token: Optional[str] = Field(None)
    expires_at: Optional[str] = Field(None)  # ISO format string for expiration time
    created_at: Optional[str] = Field(None)  # ISO format string for creation time
