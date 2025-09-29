from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel, ConfigDict


class AuthInformation(BaseModel):
    """
    Represents the information about the authenticated user or client.
    """

    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )

    redirect_uri: Optional[str]
    """The URI to redirect to after authentication, if applicable."""
    claims: Optional[dict[str, Any]]
    """The claims associated with the authenticated user or client."""
    audience: Optional[str | List[str]]
    """The audience for which the token is intended, can be a single string or a list of strings."""
    expires_at: Optional[datetime]
    """The expiration time of the authentication token, if applicable."""

    email: Optional[str]
    """The email of the authenticated user, if available."""
    subject: Optional[str]
    """The subject (sub) claim from the token, representing the unique identifier of the user."""

    user_name: Optional[str]
    """The name of the authenticated user, if available."""
