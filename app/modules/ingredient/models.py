from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.product_ingredient.models import ProductIngredient


class Ingredient(SQLModel, table=True):

    __tablename__ = "ingredient"  # type: ignore

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, min_length=2, unique=True, index=True)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    products: list["ProductIngredient"] = Relationship(back_populates="ingredient")
