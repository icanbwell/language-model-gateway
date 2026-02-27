from typing import Optional, Dict

from pydantic import BaseModel, ConfigDict, Field

from oidcauthlib.auth.models.auth import AuthInformation


class RequestInformation(BaseModel):
    """
    Represents the information about the request being processed.
    """

    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )

    auth_information: Optional[AuthInformation] = Field(
        default=None,
        description="The authentication information associated with the request, if available.",
    )

    user_id: Optional[str] = Field(
        default=None,
        description="The user ID associated with the request, if available.",
    )

    user_email: Optional[str] = Field(
        default=None,
        description="The user email associated with the request, if available.",
    )

    user_name: Optional[str] = Field(
        default=None,
        description="The user name associated with the request, if available.",
    )

    request_id: str = Field(description="The unique identifier for the request.")

    conversation_thread_id: Optional[str] = Field(
        default=None,
        description="The conversation thread identifier for the request, if applicable.",
    )

    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="The HTTP headers associated with the request.",
    )

    client_id: str | None = Field(
        default=None,
        description="The client ID associated with the request, if available.",
    )

    enable_debug_logging: bool = Field(
        default=False,
        description="Indicates whether debug logging is enabled for this request.",
    )
