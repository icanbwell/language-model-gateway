from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel


class AuthInformation(BaseModel):
    redirect_uri: Optional[str]
    claims: Optional[dict[str, Any]]
    audience: Optional[str | List[str]]
    expires_at: Optional[datetime]
