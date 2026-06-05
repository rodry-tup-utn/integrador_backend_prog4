from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import List, Literal
from decimal import Decimal
from app.modules.ingredient.models import MeasurementUnit


class IngredientCreate(SQLModel):
    name: str = Field(max_length=100, min_length=2)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool = Field(default=False)
    stock: Decimal = Field(default=0, ge=0)
    measurement_unit: MeasurementUnit


class IngredientPublic(SQLModel):
    id: int
    name: str
    description: str | None
    is_allergen: bool


class IngredientPrivate(IngredientPublic):
    stock: Decimal
    measurement_unit: MeasurementUnit
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class IngredientUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool | None = Field(default=None)
    measurement_unit: MeasurementUnit | None = Field(default=None)
    stock: Decimal | None = Field(ge=0, default=None)


class IngredientList(SQLModel):
    data: List[IngredientPublic]
    total: int


class IngredientListFull(SQLModel):
    data: List[IngredientPrivate]
    total: int


class IngredientFilters(SQLModel):
    search: str | None = None
    is_allergen: bool | None = None
    offset: int = 0
    limit: int = 20
    sort_by: Literal["name", "created_at"] = "name"
    order: Literal["asc", "desc"] = "asc"


class UpdateStockIngredient(SQLModel):
    stock: Decimal = Field(ge=0)
