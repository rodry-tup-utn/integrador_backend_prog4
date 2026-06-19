from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Column, DateTime, JSON
from app.modules.order_item.models import OrderItem
from enum import StrEnum
from app.modules.ingredient.models import MeasurementUnit


class ProductType(StrEnum):
    FINAL = "FINAL"
    MANUFACTURED = "MANUFACTURED"


if TYPE_CHECKING:
    from app.modules.product_category.models import ProductCategoryLink
    from app.modules.product_ingredient.models import ProductIngredient


class Product(SQLModel, table=True):
    """Tabla de Productos"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=3, max_length=150, unique=True)
    description: str | None = Field(default=None, max_length=255)
    base_price: Decimal = Field(gt=0)
    stock: int | None = Field(ge=0, default=None)
    sales_unit: str | None = Field(
        default=None, foreign_key="measurement_unit.code", max_length=20
    )
    images_url: list[str] | None = Field(
        default=None, sa_column=Column(JSON)
    )
    available: bool = Field(default=True)
    type: ProductType

    measurement_unit: MeasurementUnit | None = Relationship(back_populates="products")

    category_links: list["ProductCategoryLink"] = Relationship(back_populates="product")
    ingredients: list["ProductIngredient"] = Relationship(back_populates="product")
    order_items: list["OrderItem"] = Relationship(back_populates="product")

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
