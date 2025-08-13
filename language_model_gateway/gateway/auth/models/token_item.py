from typing import Optional

from pydantic import Field

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from datetime import datetime, UTC


class TokenItem(BaseDbModel):
    """
    Represents a token item in the database.
    """

    created: Optional[datetime] = Field(None)
    """The creation time of the token as a datetime object."""
    updated: Optional[datetime] = Field(None)
    """The last update time of the token as a datetime object."""
    refreshed: Optional[datetime] = Field(None)
    """The last refresh time of the token as a datetime object."""

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
    access_token_expires: Optional[datetime] = Field(None)
    """The expiration time of the token as a datetime object."""
    access_token_issued: Optional[datetime] = Field(None)
    """The creation time of the token as a datetime object."""
    id_token_expires: Optional[datetime] = Field(None)
    """The expiration time of the ID token as a datetime object."""
    id_token_issued: Optional[datetime] = Field(None)
    """The creation time of the ID token as a datetime object."""
    refresh_token_expires: Optional[datetime] = Field(None)
    """The expiration time of the refresh token as a datetime object."""
    refresh_token_issued: Optional[datetime] = Field(None)
    """The creation time of the refresh token as a datetime object."""

    @staticmethod
    def _make_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Ensure a datetime is offset-aware in UTC. If offset-naive, convert to UTC-aware.
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def is_valid_id_token(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if self.id_token_expires:
            now: datetime = datetime.now(UTC)
            expires: datetime | None = self._make_aware_utc(self.id_token_expires)
            return not expires or expires > now
        return False

    def is_valid_refresh_token(self) -> bool:
        """
        Check if the refresh token is valid based on its expiration time.
        Returns:
            bool: True if the refresh token is valid, False otherwise.
        """
        if self.refresh_token_expires:
            now: datetime = datetime.now(UTC)
            expires: datetime | None = self._make_aware_utc(self.refresh_token_expires)
            return not expires or expires > now
        return False

    def is_valid_access_token(self) -> bool:
        """
        Check if the access token is valid based on its expiration time.
        Returns:
            bool: True if the access token is valid, False otherwise.
        """
        if self.access_token_expires:
            now: datetime = datetime.now(UTC)
            expires: datetime | None = self._make_aware_utc(self.access_token_expires)
            return not expires or expires > now
        return False
