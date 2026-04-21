from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class Category(SQLModel, table=True):
    """Tabla de categoria"""

    id: int = Field(default=None, primary_key=True)
    parent_id: int = Field(default=None, foreign_key="category.id")
    name: str = Field(max_length=50, min_length=4, unique=True, index=True)
    description: str | None = Field(default=None, min_length=5, max_length=255)
    image_url: str | None = Field(255)
    created_at: datetime = Field(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
