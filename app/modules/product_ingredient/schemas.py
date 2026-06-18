from sqlmodel import SQLModel, Field
from typing import List
from decimal import Decimal


class ProductIngredientCreate(SQLModel):
    is_removable: bool = Field(default=False)
    quantity_ingredient: Decimal = Field(ge=0)


class ProductIngredientPublic(SQLModel):
    product_id: int
    ingredient_id: int
    is_removable: bool
    quantity_ingredient: Decimal


class ProductIngredientUpdate(SQLModel):
    is_removable: bool | None = None
    quantity_ingredient: Decimal | None = Field(ge=0, default=None)


# Para mostrar un ingrediente dentro de la lista de un producto
class IngredientInProduct(SQLModel):
    ingredient_id: int
    name: str
    description: str | None
    is_removable: bool
    quantity_ingredient: Decimal
    measurement_unit_code: str


# Para mostrar un producto con su lista de ingredientes
class ProductWithIngredients(SQLModel):
    product_id: int
    name: str
    ingredients: List[IngredientInProduct]


class ProductIngredientBatchItem(SQLModel):
    ingredient_id: int
    is_removable: bool = Field(default=False)
    quantity_ingredient: Decimal = Field(ge=0, default=0)


class ProductIngredientBatchCreate(SQLModel):
    ingredients: list[ProductIngredientBatchItem]
