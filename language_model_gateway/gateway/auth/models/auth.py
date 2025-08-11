from typing import Optional

from pydantic import BaseModel


class AuthInformation(BaseModel):
    redirect_uri: Optional[str]
