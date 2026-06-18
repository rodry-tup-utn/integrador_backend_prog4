from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    token_hash: str = Field(nullable=False, index=True)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
