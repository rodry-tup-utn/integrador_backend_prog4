from sqlmodel import SQLModel, Field
from pydantic import field_validator
from app.modules.user.models import Role, UserRoleLink


class UserCreate(SQLModel):
    name: str = Field(
        max_length=80,
        min_length=4,
    )
    lastname: str = Field(max_length=80, min_length=4)
    email: str = Field(max_length=255, min_length=8)
    phone_number: str | None = Field(max_length=20, default=None)
    password: str = Field(max_length=255, min_length=8)


class UserBase(SQLModel):
    id: int
    name: str
    lastname: str
    email: str


class UserUpdate(SQLModel):
    name: str | None = None
    lastname: str | None = None
    phone_number: str | None = None
    email: str | None = None


class UserPrivate(UserBase):
    roles: list[Role]

    @field_validator("roles", mode="before")
    @classmethod
    def convert_roles(cls, v):
        if v and isinstance(v[0], UserRoleLink):
            return [
                Role.model_validate(link.role_user)
                for link in v
                if link.role_user and link.expires_at is None
            ]
        return v


class UserLogin(SQLModel):
    email: str = Field(max_length=255, min_length=4)
    password: str = Field(max_length=255, min_length=8)


class UserAuthCredentials(SQLModel):
    id: int
    name: str
    roles: list[str]
    hashed_pass: str


class UserList(SQLModel):
    data: list[UserPrivate]
    total: int
