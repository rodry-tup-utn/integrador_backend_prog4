from sqlmodel import SQLModel, Field
from datetime import datetime
from decimal import Decimal


class UserCreate(SQLModel):
    name: str = Field(
        max_length=80,
        min_length=4,
    )
    lastname: str = Field(max_length=80, min_length=4)
    email: str = Field(max_length=255, min_length=8)
    phone_number: str | None = Field(max_length=20, default=None)
    password: str = Field(max_length=255, min_length=8)


class UserCreateByAdmin(UserCreate):
    role_code: str = Field(max_length=20, min_length=1)


class UserResponse(SQLModel):
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


class AddressRead(SQLModel):
    id: int
    alias: str
    line_one: str
    line_two: str | None
    city: str
    province: str
    zip_code: str
    latitude: Decimal
    longitude: Decimal
    is_main: bool

    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class AddressUpdate(SQLModel):
    alias: str | None = None
    line_one: str | None = None
    line_two: str | None = None
    city: str | None = None
    province: str | None = None
    zip_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_main: bool | None = None


class AddressCreate(SQLModel):
    alias: str = Field(max_length=255, min_length=3)
    line_one: str = Field(max_length=255)
    line_two: str | None = Field(max_length=255, default=None)
    city: str = Field(max_length=100)
    province: str = Field(max_length=100)
    zip_code: str = Field(max_length=10)
    latitude: Decimal = Field(
        ge=-90.0, le=90.0, description="Latitud en grados, -90 a 90"
    )
    longitude: Decimal = Field(
        ge=-180.0, le=180.0, description="Longitud en grados, -180 a 180"
    )
    is_main: bool | None = Field(default=False)


class UserRoleRead(SQLModel):
    role_user: RoleRead
    assigned_by_id: int
    expires_at: datetime | None
    created_at: datetime


class UserAdminRead(UserResponse):
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
    roles: list[UserRoleRead]


class UserDetailRead(UserResponse):
    roles: list[UserRoleRead]


class UserProfileRead(UserResponse):
    roles: list[UserRoleRead]
    addresses: list[AddressRead]


class UserAuthData(SQLModel):
    id: int
    name: str
    roles: list[str]
    hashed_pass: str


class UserSessionRead(UserResponse):
    roles: list[str]


class TokenPayloadData(SQLModel):
    id: int
    name: str
    roles: list[str]


class UserPaginatedRead(SQLModel):
    data: list[UserAdminRead]
    total: int
