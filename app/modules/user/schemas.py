from sqlmodel import SQLModel, Field
from pydantic import field_validator
from app.modules.user.models import Role, UserRoleLink
from datetime import datetime


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


class RoleRead(SQLModel):
    code: str
    name: str
    description: str


class DeliveryAdressRead(SQLModel):
    id: int
    alias: str
    line_one: str
    line_two: str | None
    city: str
    province: str
    zip_code: str
    latitud: float
    longitude: float
    is_main: bool

    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class DeliveryAdressUpdate(SQLModel):
    alias: str | None = None
    line_one: str | None = None
    line_two: str | None = None
    city: str | None = None
    province: str | None = None
    zip_code: str | None = None
    latitud: float | None = None
    longitude: float | None = None
    is_main: bool | None = None


class DeliveryAdressCreate(SQLModel):
    alias: str = Field(max_length=255, min_length=3)
    line_one: str = Field(max_length=255)
    line_two: str | None = Field(max_length=255, default=None)
    city: str = Field(max_length=100)
    province: str = Field(max_length=100)
    zip_code: str = Field(max_length=10)
    latitud: float = Field(ge=-90.0, le=90.0, description="Latitud en grados, -90 a 90")
    longitude: float = Field(
        ge=-180.0, le=180.0, description="Longitud en grados, -180 a 180"
    )
    is_main: bool | None = Field(default=False)


class UserRole(SQLModel):
    role_code: str
    role_user: RoleRead
    assigned_by_id: int
    expires_at: datetime | None
    created_at: datetime


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


class UserDetail(UserBase):
    roles: list[UserRole]


class UserProfile(UserBase):
    roles: list[UserRole]
    addresses: list[DeliveryAdressRead]


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
