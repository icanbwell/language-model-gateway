from pydantic import BaseModel


class AuthConfig(BaseModel):
    audience: str
    issuer: str
    client_id: str | None
    client_secret: str | None
    well_known_uri: str | None
