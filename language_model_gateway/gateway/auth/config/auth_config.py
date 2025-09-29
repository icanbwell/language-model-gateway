from pydantic import BaseModel, ConfigDict


class AuthConfig(BaseModel):
    """
    Represent the configuration for an auth provider.  Usually read from environment variables.
    """

    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )

    auth_provider: str
    """The name of the auth provider, typically used to identify the provider in logs and error messages."""
    audience: str
    """The audience for the auth provider, typically the API or service that the token is intended for."""
    issuer: str
    """The issuer of the token, typically the URL of the auth provider."""
    client_id: str | None
    """The client ID for the auth provider, used to identify the application making the request."""
    client_secret: str | None
    """The client secret for the auth provider, used to authenticate the application making the request."""
    well_known_uri: str | None
    """The URI to the well-known configuration of the auth provider, used to discover endpoints and other metadata."""
