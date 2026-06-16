from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from decimal import Decimal

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.product_ingredient.models import ProductIngredient


class MeasurementUnit(SQLModel, table=True):

    __tablename__ = "measurement_unit"  # type: ignore

    code: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=50, unique=True, nullable=False)
    symbol: str = Field(max_length=10, unique=True, nullable=False)
    unit_type: str = Field(max_length=20, nullable=False)


class Ingredient(SQLModel, table=True):

    __tablename__ = "ingredient"  # type: ignore

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, min_length=2, unique=True, index=True)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool = Field(default=False)
    measurement_unit_code: str = Field(
        foreign_key="measurement_unit.code", max_length=20
    )
    stock: Decimal = Field(default=None, ge=0)
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
