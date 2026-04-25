from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.modules.product.models import Product


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    parent_id: int | None = Field(
        default=None, foreign_key="category.id", nullable=True
    )

    name: str = Field(max_length=50, min_length=4, unique=True, index=True)
    description: str | None = Field(default=None, min_length=5, max_length=255)
    image_url: str | None = Field(default=None, max_length=255)

    parent: Optional["Category"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Category.id"}
    )

    children: List["Category"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    products: List["Product"] = Relationship(back_populates="category")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
