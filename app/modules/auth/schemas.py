from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal


class JWTPayload(BaseModel):
    sub: str
    role: str
    name: str
    exp: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class UserTokenData(BaseModel):
    id: int
    role: str
    name: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserTokenData
