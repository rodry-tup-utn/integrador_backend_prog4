from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped
from decimal import Decimal


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=80, min_length=4, nullable=False)
    lastname: str = Field(max_length=80, min_length=4, nullable=False)
    email: str = Field(
        max_length=255,
        min_length=8,
        index=True,
        unique=True,
        nullable=False,
    )
    phone_number: str | None = Field(max_length=20, default=None)
    hashed_pass: str = Field()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)

    roles: Mapped[list["UserRoleLink"]] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.user_id]"},
    )

    assigned_roles: Mapped[list["UserRoleLink"]] = Relationship(
        back_populates="assigned_by",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.assigned_by_id]"},
    )
    delivery_adress: Mapped[list["DeliveryAdress"]] = Relationship(
        back_populates="user"
    )


class Role(SQLModel, table=True):
    code: str = Field(
        primary_key=True,
        max_length=20,
        min_length=1,
    )
    name: str = Field(max_length=50, min_length=1)
    description: str = Field(max_length=255)
    users: list["UserRoleLink"] = Relationship(back_populates="role_user")


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_role"  # type: ignore
    user_id: int = Field(
        foreign_key="user.id",
        primary_key=True,
    )
    role_code: str = Field(
        foreign_key="role.code",
        primary_key=True,
    )

    assigned_by_id: int = Field(foreign_key="user.id")
    expires_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: User | None = Relationship(
        back_populates="roles",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.user_id]"},
    )

    role_user: Role | None = Relationship(back_populates="users")
    assigned_by: User | None = Relationship(
        back_populates="assigned_roles",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.assigned_by_id]"},
    )


class DeliveryAdress(SQLModel, table=True):
    __tablename__ = "delivery_adress"  # type: ignore

    id: int | None = Field(primary_key=True, default=None)
    user_id: int = Field(foreign_key="user.id")

    alias: str = Field(max_length=50, min_length=3)
    line_one: str = Field(max_length=255, min_length=3)
    line_two: str | None = Field(max_length=255, default=None)
    city: str = Field(max_length=100)
    province: str = Field(max_length=100)
    zip_code: str = Field(max_length=10)
    latitud: float = Field(ge=-90.0, le=90.0, description="Latitud en grados, -90 a 90")
    longitude: float = Field(
        ge=-180.0, le=180.0, description="Longitud en grados, -180 a 180"
    )
    is_main: bool = Field(default=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)

    user: User = Relationship(back_populates="delivery_adress")
