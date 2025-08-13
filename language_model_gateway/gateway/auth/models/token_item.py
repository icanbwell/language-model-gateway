from typing import Optional

from pydantic import Field

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from datetime import datetime, UTC


class TokenItem(BaseDbModel):
    """
    Represents a token item in the database.
    """

    issuer: str = Field()
    """The issuer of the token, typically the authorization server."""
    audience: str = Field()
    """The intended audience for the token, usually the resource server."""
    email: str = Field()
    """The email associated with the token, used for user identification."""
    url: Optional[str] = Field(None)
    """The URL associated with the token, if applicable."""
    access_token: Optional[str] = Field(None)
    """The access token used for authentication."""
    id_token: Optional[str] = Field(None)
    """The ID token containing user information."""
    expires_at: Optional[str] = Field(None)  # ISO format string for expiration time
    """The expiration time of the token in ISO format."""
    created_at: Optional[str] = Field(None)  # ISO format string for creation time
    """The creation time of the token in ISO format."""

    def is_valid(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if self.expires_at:
            expiration_time = datetime.fromisoformat(self.expires_at)
            if expiration_time.tzinfo:
                now = datetime.now(UTC).replace(tzinfo=expiration_time.tzinfo)
            else:
                now = datetime.now(UTC)
            return expiration_time > now
        return False
