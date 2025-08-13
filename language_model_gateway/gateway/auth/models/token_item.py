from typing import Optional

from pydantic import Field

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from datetime import datetime, UTC


class TokenItem(BaseDbModel):
    """
    Represents a token item in the database.
    """

    created: Optional[str] = Field(None)
    """The creation time of the token in ISO format."""
    updated: Optional[str] = Field(None)
    """The last update time of the token in ISO format."""
    refreshed: Optional[str] = Field(None)
    """The last refresh time of the token in ISO format."""

    issuer: str = Field()
    """The issuer of the token, typically the authorization server."""
    audience: str = Field()
    """The intended audience for the token, usually the resource server."""
    email: str = Field()
    """The email associated with the token, used for user identification."""
    subject: str = Field()
    """The subject of the token, typically the user ID or unique identifier."""
    url: Optional[str] = Field(None)
    """The URL associated with the token, if applicable."""
    access_token: Optional[str] = Field(None)
    """The access token used for authentication."""
    id_token: Optional[str] = Field(None)
    """The ID token containing user information."""
    refresh_token: Optional[str] = Field(None)
    """The refresh token used to obtain new access tokens."""
    access_token_expires: Optional[str] = Field(
        None
    )  # ISO format string for expiration time
    """The expiration time of the token in ISO format."""
    access_token_issued: Optional[str] = Field(
        None
    )  # ISO format string for creation time
    """The creation time of the token in ISO format."""
    id_token_expires: Optional[str] = Field(None)
    """The expiration time of the ID token in ISO format."""
    id_token_issued: Optional[str] = Field(
        None
    )  # ISO format string for ID token creation time
    """The creation time of the ID token in ISO format."""
    refresh_token_expires: Optional[str] = Field(
        None
    )  # ISO format string for refresh token expiration
    """The expiration time of the refresh token in ISO format."""
    refresh_token_issued: Optional[str] = Field(
        None
    )  # ISO format string for refresh token creation time
    """The creation time of the refresh token in ISO format."""

    def is_valid_id_token(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if self.id_token_expires:
            expiration_time: datetime = datetime.fromisoformat(self.id_token_expires)
            if expiration_time.tzinfo:
                now = datetime.now(UTC).replace(tzinfo=expiration_time.tzinfo)
            else:
                now = datetime.now(UTC)
            return expiration_time > now
        return False

    def is_valid_refresh_token(self) -> bool:
        """
        Check if the refresh token is valid based on its expiration time.
        Returns:
            bool: True if the refresh token is valid, False otherwise.
        """
        if self.refresh_token_expires:
            expiration_time: datetime = datetime.fromisoformat(
                self.refresh_token_expires
            )
            if expiration_time.tzinfo:
                now = datetime.now(UTC).replace(tzinfo=expiration_time.tzinfo)
            else:
                now = datetime.now(UTC)
            return expiration_time > now
        return False

    def is_valid_access_token(self) -> bool:
        """
        Check if the access token is valid based on its expiration time.
        Returns:
            bool: True if the access token is valid, False otherwise.
        """
        if self.access_token_expires:
            expiration_time: datetime = datetime.fromisoformat(
                self.access_token_expires
            )
            if expiration_time.tzinfo:
                now = datetime.now(UTC).replace(tzinfo=expiration_time.tzinfo)
            else:
                now = datetime.now(UTC)
            return expiration_time > now
        return False
