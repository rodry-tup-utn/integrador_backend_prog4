from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import List
from app.modules.user.models import Role


class UserCreate(SQLModel):
    name: str = Field(
        max_length=80,
        min_length=4,
    )
    lastname: str = Field(max_length=80, min_length=4)
    email: str = Field(max_length=255, min_length=8)
    phone_number: str | None = Field(max_length=20, default=None)
    password: str = Field(max_length=255, min_length=8)
    role: Role = Field(default=Role.PUBLIC)


class UserBase(SQLModel):
    id: int
    name: str
    lastname: str
    email: str


class UserUpdate(SQLModel):
    name: str | None = None
    lastname: str | None = None
    phone_number: str | None = None
    name: str | None = None
    email: str | None = None


class UserPrivate(UserBase):
    role: Role
    deleted_at: datetime | None


class UserLogin(SQLModel):
    email: str = Field(max_length=255, min_length=4)
    password: str = Field(max_length=255, min_length=8)


class UserAuthCredentials(SQLModel):
    id: int
    email: str
    role: Role
    hashed_pass: str


class UserList(SQLModel):
    data: list[UserPrivate]
    total: int
