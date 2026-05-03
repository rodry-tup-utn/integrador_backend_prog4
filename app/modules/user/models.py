from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    PUBLIC = "PUBLIC"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=80, min_length=4, nullable=False)
    lastname: str = Field(max_length=80, min_length=4, nullable=False)
    email: str = Field(
        max_length=255, min_length=8, index=True, unique=True, nullable=False
    )
    phone_number: str | None = Field(max_length=20, default=None)
    hashed_pass: str = Field()
    role: Role = Field(default=Role.PUBLIC)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
