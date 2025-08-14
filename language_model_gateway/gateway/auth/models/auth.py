from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class AuthInformation(BaseModel):
    redirect_uri: Optional[str]
    claims: Optional[dict[str, Any]]
    audience: Optional[str]
    expires_at: Optional[datetime]
