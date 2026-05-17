from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal


class JWTPayload(BaseModel):
    sub: str
    role: list[str]
    name: str
    exp: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class UserTokenData(BaseModel):
    id: int
    role: list[str]
    name: str
