from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import List


class IngredientCreate(SQLModel):
    name: str = Field(max_length=100, min_length=2)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool = Field(default=False)


class IngredientPublic(SQLModel):
    id: int
    name: str
    description: str
    is_allergen: bool


class IngredientPrivate(IngredientPublic):
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class IngredientUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    is_allergen: bool | None = Field(default=False)


class IngredientList(SQLModel):
    data: List[IngredientPublic]
    total: int
