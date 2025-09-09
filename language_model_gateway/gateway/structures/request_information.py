from typing import Optional, Dict

from pydantic import BaseModel

from language_model_gateway.gateway.auth.models.auth import AuthInformation


class RequestInformation(BaseModel):
    """
    Represents the information about the request being processed.
    """

    auth_information: Optional[AuthInformation]
    """ The authentication information associated with the request, if available."""

    user_id: Optional[str]
    """ The user ID associated with the request, if available."""

    user_email: Optional[str]
    """ The user email associated with the request, if available."""

    request_id: str
    """ The unique identifier for the request, if available."""

    conversation_thread_id: Optional[str]
    """ The conversation thread identifier for the request, if applicable."""

    headers: Dict[str, str]
    """ The headers associated with the request."""
