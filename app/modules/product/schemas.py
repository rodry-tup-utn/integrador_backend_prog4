from sqlmodel import SQLModel, Field
from datetime import datetime
from decimal import Decimal


class ProductCreate(SQLModel):
    name: str = Field(max_length=150, min_length=3)
    description: str | None = Field(default=None, max_length=255)
    base_price: Decimal = Field(gt=0)
    images_url: str | None = Field(default=None, max_length=255)
    category_id: int = Field(ge=1)


class CategoryBase(SQLModel):
    id: int
    name: str
    image_url: str | None


class ProductPublic(SQLModel):
    id: int
    base_price: Decimal
    name: str
    description: str | None
    images_url: str | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class ProductPublicFull(ProductPublic):
    primary_category: CategoryBase
    categories: list[CategoryBase] | None


class ProductList(SQLModel):
    data: list[ProductPublic]
    total: int


class ProductUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=150, min_length=3)
    description: str | None = Field(default=None, max_length=255, min_length=3)
    base_price: Decimal | None = Field(default=None, gt=0)
    images_url: str | None = Field(default=None, max_length=255)
    category_id: int | None = Field(default=None, ge=1)
