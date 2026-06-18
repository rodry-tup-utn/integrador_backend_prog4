from sqlmodel import SQLModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Annotated
from pydantic import Field as PydanticField
from app.modules.product.models import ProductType
from app.modules.product_ingredient.schemas import ProductIngredientBatchItem


class ProductCreate(SQLModel):
    name: str = Field(max_length=150, min_length=3)
    description: str | None = Field(default=None, max_length=255)
    base_price: Decimal = Field(gt=0)
    stock: int | None = Field(ge=0, default=None)
    sales_unit: str | None = Field(default=None, max_length=20)
    images_url: str | None = Field(default=None, max_length=255)
    category_id: int = Field(ge=1)
    type: ProductType = Field(default=ProductType.FINAL)
    ingredients: list[ProductIngredientBatchItem] = Field(default_factory=list)


class CategoryBase(SQLModel):
    id: int
    name: str
    image_url: str | None


class IngredientBase(SQLModel):
    ingredient_id: int
    name: str
    description: str | None
    is_removable: bool
    is_allergen: bool
    quantity: Decimal


class ProductPublic(SQLModel):
    id: int
    base_price: Decimal
    stock: int | None
    sales_unit: str | None = None
    name: str
    description: str | None
    images_url: str | None
    available: bool
    type: ProductType


class ProductAdmin(ProductPublic):
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class ProductDetail(ProductPublic):
    primary_category: CategoryBase
    categories: list[CategoryBase] | None
    ingredients: list[IngredientBase] | None


class ProductAdminDetail(ProductDetail):
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class ProductList(SQLModel):
    data: list[ProductPublic]
    total: int


class ProductListAdmin(SQLModel):
    data: list[ProductAdmin]
    total: int


class ProductUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=150, min_length=3)
    description: str | None = Field(default=None, max_length=255, min_length=3)
    base_price: Decimal | None = Field(default=None, gt=0)
    images_url: str | None = Field(default=None, max_length=255)
    category_id: int | None = Field(default=None, ge=1)
    stock: int | None = Field(ge=0, default=None)
    sales_unit: str | None = Field(default=None, max_length=20)


class UpdateType(SQLModel):
    type: ProductType


class ProductFilters(SQLModel):
    search: Annotated[str | None, PydanticField(max_length=20, min_length=3)] = None
    category_id: Annotated[int | None, PydanticField(ge=1)] = None
    max_price: Annotated[Decimal | None, PydanticField(ge=0)] = None
    min_price: Annotated[Decimal | None, PydanticField(ge=0)] = None
    available: bool | None = None
    type: ProductType | None = None

    offset: Annotated[int, PydanticField(ge=0)] = 0
    limit: Annotated[int, PydanticField(ge=1)] = 20

    sort_by: Literal["name", "base_price"] = "name"
    order: Literal["asc", "desc"] = "asc"


class UpdateStock(SQLModel):
    stock: int


class UpdateAbailability(SQLModel):
    available: bool
