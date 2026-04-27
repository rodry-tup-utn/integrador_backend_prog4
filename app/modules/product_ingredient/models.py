from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.product.models import Product
    from app.modules.ingredient.models import Ingredient


class ProductIngredient(SQLModel, table=True):
    """Tabla intermedia entre Producto e Ingrediente con atributo propio"""

    __tablename__ = "product_ingredient"

    product_id: int = Field(foreign_key="product.id", primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", primary_key=True)
    is_removable: bool = Field(default=False)

    product: "Product" = Relationship(back_populates="ingredients")
    ingredient: "Ingredient" = Relationship(back_populates="products")
