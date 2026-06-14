from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.category.models import Category
    from app.modules.product.models import Product


class ProductCategoryLink(SQLModel, table=True):
    __tablename__ = "product_category_link"  # type: ignore

    product_id: int = Field(primary_key=True, foreign_key="product.id")
    category_id: int = Field(primary_key=True, foreign_key="category.id")

    is_primary: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )

    product: "Product" = Relationship(back_populates="category_links")
    category: "Category" = Relationship(back_populates="product_links")
