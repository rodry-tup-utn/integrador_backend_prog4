from sqlmodel import SQLModel, Field
from typing import List


class ProductIngredientCreate(SQLModel):
    is_removable: bool = Field(default=False)


class ProductIngredientPublic(SQLModel):
    product_id: int
    ingredient_id: int
    is_removable: bool


class ProductIngredientUpdate(SQLModel):
    is_removable: bool


# Para mostrar un ingrediente dentro de la lista de un producto
class IngredientInProduct(SQLModel):
    ingredient_id: int
    name: str
    description: str | None
    is_removable: bool


# Para mostrar un producto con su lista de ingredientes
class ProductWithIngredients(SQLModel):
    product_id: int
    name: str
    ingredients: List[IngredientInProduct]
