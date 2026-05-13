from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from decimal import Decimal

if TYPE_CHECKING:
    from app.modules.product_category.models import ProductCategoryLink
    from app.modules.product_ingredient.models import ProductIngredient


class Product(SQLModel, table=True):
    """Tabla de Productos"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=3, max_length=150, unique=True)
    description: str | None = Field(default=None, max_length=255)
    base_price: Decimal = Field(gt=0)
    stock: int = Field(ge=0, default=0)
    images_url: str | None = Field(default=None)
    available: bool = Field(default=True)

    category_links: list["ProductCategoryLink"] = Relationship(back_populates="product")
    ingredients: list["ProductIngredient"] = Relationship(back_populates="product")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
