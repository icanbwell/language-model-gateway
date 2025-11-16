from typing import Optional

from bson import ObjectId
from oidcauthlib.auth.models.base_db_model import BaseDbModel
from pydantic import Field

from datetime import datetime, UTC

from oidcauthlib.auth.models.token import Token


class TokenCacheItem(BaseDbModel):
    """
    Represents a token cache item in the database.
    """

    created: datetime = Field()
    """The creation time of the token as a datetime object."""
    updated: Optional[datetime] = Field(default=None)
    """The last update time of the token as a datetime object."""
    refreshed: Optional[datetime] = Field(default=None)
    """The last refresh time of the token as a datetime object."""

    auth_provider: str = Field()
    """The authentication provider associated with the token."""
    issuer: str | None = Field(default=None)
    """The issuer of the token, typically the authorization server."""
    audience: str = Field()
    """The intended audience for the token, usually the resource server."""
    email: str = Field()
    """The email associated with the token, used for user identification."""
    subject: str = Field()
    """The subject of the token, typically the user ID or unique identifier."""
    referring_email: str = Field()
    """The email of the original token that is linked to this token, if applicable."""
    referring_subject: str = Field()
    """The subject of the original token that is linked to this token, if applicable."""
    referrer: Optional[str] = Field(default=None)
    """The URL associated with the token, if applicable."""
    access_token: Optional[Token] = Field(default=None)
    """The access token used for authentication."""
    id_token: Optional[Token] = Field(default=None)
    """The ID token containing user information."""
    refresh_token: Optional[Token] = Field(default=None)
    """The refresh token used to obtain new access tokens."""

    def is_valid_id_token(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        return self.id_token.is_valid() if self.id_token else False

    def is_valid_refresh_token(self) -> bool:
        """
        Check if the refresh token is valid based on its expiration time.
        Returns:
            bool: True if the refresh token is valid, False otherwise.
        """
        return self.refresh_token.is_valid() if self.refresh_token else False

    def is_valid_access_token(self) -> bool:
        """
        Check if the access token is valid based on its expiration time.
        Returns:
            bool: True if the access token is valid, False otherwise.
        """
        return self.access_token.is_valid() if self.access_token else False

    def get_access_token(self) -> Optional[Token]:
        """
        Gets the ID token if it is valid, otherwise returns the access token.
        Returns:
            Optional[str]: The id token if valid, otherwise the access token.
        """
        return self.access_token if self.access_token else None

    def get_id_token(self) -> Optional[Token]:
        """
        Gets the ID token if it is valid, otherwise returns the access token.
        Returns:
            Optional[str]: The id token if valid, otherwise the access token.
        """
        return self.id_token if self.id_token else None

    def get_refresh_token(self) -> Optional[Token]:
        """
        Gets the refresh token if it is valid.
        Returns:
            Optional[str]: The refresh token if valid, otherwise None.
        """
        return self.refresh_token if self.refresh_token else None

    @classmethod
    def create(
        cls,
        *,
        token: Token,
        auth_provider: str,
        referring_email: str,
        referring_subject: str,
    ) -> "TokenCacheItem":
        # see what the token this is

        audience: str | None = None
        if isinstance(token.audience, list):
            if len(token.audience) == 1:
                audience = token.audience[0]
        elif isinstance(token.audience, str):
            audience = token.audience

        if audience is None:
            raise ValueError("Audience must be a string or a list with one string.")

        if token.email is None:
            raise ValueError("Token must have an email claim.")
        if token.subject is None:
            raise ValueError("Token must have a subject claim.")

        token_cache_item: TokenCacheItem = TokenCacheItem(
            _id=ObjectId(),
            created=datetime.now(UTC),
            updated=None,
            refreshed=None,
            auth_provider=auth_provider,
            issuer=token.issuer,
            audience=audience,
            email=token.email,
            subject=token.subject,
            referrer=None,
            access_token=token,
            id_token=None,
            refresh_token=None,
            referring_email=referring_email,
            referring_subject=referring_subject,
        )
        if token.is_id_token:
            token_cache_item.id_token = token
        elif token.is_access_token:
            token_cache_item.access_token = token
        elif token.is_refresh_token:
            token_cache_item.refresh_token = token
        else:
            raise ValueError(
                f"Token type must be id, bearer or refresh but was: {token.token_type}"
            )

        return token_cache_item

    def is_expired(self) -> bool:
        """
        Check if the token cache item is expired based on the access token.
        Returns:
            bool: True if the access token is expired, False otherwise.
        """
        return (
            not self.id_token.is_valid()
            if self.id_token
            else not self.access_token.is_valid()
            if self.access_token
            else True
        )
