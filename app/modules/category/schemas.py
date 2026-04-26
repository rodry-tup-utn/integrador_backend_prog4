from __future__ import annotations
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import List


class CategoryCreate(SQLModel):
    parent_id: int | None = Field(default=None)
    name: str = Field(max_length=30, min_length=4)
    description: str | None = Field(default=None, max_length=255, min_length=4)
    image_url: str | None = Field(default=None, max_length=255, min_length=5)


class CategoryPublic(SQLModel):
    id: int
    parent_id: int | None
    name: str
    description: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class CategoryPublicTree(CategoryPublic):
    children: list[CategoryPublicTree]


class CategoryTree(SQLModel):
    id: int
    name: str
    parent_id: int | None
    children: list[CategoryTree]


class CategoryUpdate(SQLModel):
    parent_id: int | None = Field(default=None)
    name: str | None = Field(default=None, min_length=4, max_length=50)
    description: str | None = Field(default=None, max_length=255, min_length=5)
    image_url: str | None = Field(default=None, max_length=255, min_length=5)


class CategoryList(SQLModel):
    data: List[CategoryPublic]
    total: int
