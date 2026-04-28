from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.category.models import Category
    from app.modules.product.models import Product


class ProductCategoryLink(SQLModel, table=True):
    __tablename__ = "product_category_link"  # type: ignore

    product_id: int = Field(primary_key=True, foreign_key="product.id")
    category_id: int = Field(primary_key=True, foreign_key="category.id")

    is_primary: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    product: "Product" = Relationship(back_populates="category_links")
    category: "Category" = Relationship(back_populates="product_links")
