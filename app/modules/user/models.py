from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone


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

    roles: list["UserRoleLink"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.user_id]"},
    )

    assigned_roles: list["UserRoleLink"] = Relationship(
        back_populates="assigned_by",
        sa_relationship_kwargs={"foreign_keys": "[UserRoleLink.assigned_by_id]"},
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
