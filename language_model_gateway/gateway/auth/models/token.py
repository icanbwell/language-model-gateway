import json
import logging
from datetime import datetime, UTC
from typing import Optional, Any, Dict, cast, List

from joserfc import jws
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class Token(BaseModel):
    """
    Represents a token with its associated properties.
    """

    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
    token: str = Field(...)
    """The token string."""
    expires: Optional[datetime] = Field(default=None)
    """The expiration time of the token."""
    issued: Optional[datetime] = Field(default=None)
    """The time when the token was issued."""
    claims: Optional[dict[str, Any]] = Field(default=None)
    """Additional claims associated with the token."""
    issuer: Optional[str] = Field(default=None)
    """The issuer of the token, typically the authorization server."""

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

    def is_valid(self) -> bool:
        """
        Check if the token is valid based on its expiration time.
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if self.expires is not None:
            now: datetime = datetime.now(UTC)
            expires: datetime | None = self._make_aware_utc(self.expires)
            logger.debug(
                f"Token expires at {self.expires}, current time is {datetime.now(UTC)}"
            )
            return not expires or expires > now
        else:
            logger.debug(f"Expires not set for token: {self.expires}")
            return False

    @classmethod
    def create(cls, *, token: str | None) -> Optional["Token"]:
        """
        Create a Token instance from a JWS compact token string.  Extracts claims and expiration information.
        Args:
            token (str): The JWS compact token string.
        """
        if not token:
            return None

        # parse the token but don't verify it
        token_content = jws.extract_compact(token.encode())
        claims: Dict[str, Any] = cast(Dict[str, Any], json.loads(token_content.payload))
        exp = claims.get("exp")
        iat = claims.get("iat")
        expires_dt = (
            datetime.fromtimestamp(exp, tz=UTC)
            if isinstance(exp, (int, float))
            else None
        )
        issued_dt = (
            datetime.fromtimestamp(iat, tz=UTC)
            if isinstance(iat, (int, float))
            else None
        )
        return cls(
            token=token,
            expires=cls._make_aware_utc(expires_dt),
            issued=cls._make_aware_utc(issued_dt),
            claims=claims,
            issuer=claims.get("iss"),
        )

    @property
    def token_type(self) -> str | None:
        """
        Get the type of the token.
        Returns:
            str: The type of the token, which is always "Bearer".
        """
        return self.claims.get("typ") if self.claims else None

    @property
    def is_id_token(self) -> bool:
        """
        Check if the token is an ID token.
        Returns:
            bool: True if the token is an ID token, False otherwise.
        """
        return self.token_type.lower() == "id" if self.token_type else False

    @property
    def is_access_token(self) -> bool:
        """
        Check if the token is an access token.
        Returns:
            bool: True if the token is an access token, False otherwise.
        """
        return (
            self.token_type.lower() == "bearer" if self.token_type else True
        )  # assume all other tokens are access tokens

    @property
    def is_refresh_token(self) -> bool:
        """
        Check if the token is a refresh token.
        Returns:
            bool: True if the token is a refresh token, False otherwise.
        """
        return self.token_type.lower() == "refresh" if self.token_type else False

    @property
    def subject(self) -> str | None:
        """
        Get the subject of the token.
        Returns:
            str: The subject of the token, typically the user ID or unique identifier.
        """
        return self.claims.get("sub") if self.claims else None

    @property
    def name(self) -> str | None:
        """
        Get the name associated with the token.
        Returns:
            str: The name associated with the token, typically the user's name.
        """
        return self.claims.get("name") if self.claims else None

    @property
    def email(self) -> str | None:
        """
        Get the email associated with the token.
        Returns:
            str: The email associated with the token, typically the user's email address.
        """
        return self.claims.get("email") if self.claims else None

    @property
    def audience(self) -> str | List[str] | None:
        """
        Get the audience of the token.
        Returns:
            str | List[str]: The audience of the token, which can be a single string or a list of strings.
        """
        if not self.claims:
            return None

        aud = self.claims.get("aud")
        if isinstance(aud, list):
            return aud
        return aud if isinstance(aud, str) else None
