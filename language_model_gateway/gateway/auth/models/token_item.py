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

    def is_valid(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if self.expires_at:
            from datetime import datetime

            expiration_time = datetime.fromisoformat(self.expires_at)
            return expiration_time > datetime.now()
        return False
