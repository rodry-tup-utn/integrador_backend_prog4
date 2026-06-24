from fastapi import APIRouter, Depends, Path
from sqlmodel import Session
from app.modules.product.service import ProductService
from app.modules.product.schemas import (
    ProductCreate,
    ProductList,
    ProductPublic,
    ProductDetail,
    ProductUpdate,
    ProductAdmin,
    ProductListAdmin,
    ProductAdminDetail,
    ProductFilters,
    UpdateStock,
    UpdateAbailability,
    UpdateType,
    CalculateStockRequest,
    CalculateStockResponse,
)
from app.core.database import get_session
from typing import Annotated
from app.modules.auth.dependencies import require_role
from app.modules.product_ingredient.schemas import ProductIngredientBatchItem


def get_product_service(session: Session = Depends(get_session)) -> ProductService:
    return ProductService(session)


router = APIRouter(prefix="/product", tags=["Public - Productos"])
admin_router = APIRouter(
    prefix="/admin/product",
    tags=["Admin - Product"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)

stock_router = APIRouter(
    prefix="/stock/product",
    tags=["Stock - Products"],
    dependencies=[Depends(require_role(["STOCK", "ADMIN"]))],
)


@stock_router.get("/", response_model=ProductListAdmin)
def list_all_admin(
    svc: ProductService = Depends(get_product_service),
    filters: ProductFilters = Depends(),
):
    return svc.list_all_admin(filters)


@stock_router.patch("/{id}/update")
def update_stock(
    id: Annotated[int, Path(ge=1)],
    data: UpdateStock,
    svc: ProductService = Depends(get_product_service),
) -> ProductPublic:
    return svc.update_stock(id, data)


@stock_router.patch("/{id}/available")
def set_availablility(
    id: Annotated[int, Path(ge=1)],
    data: UpdateAbailability,
    svc: ProductService = Depends(get_product_service),
) -> ProductPublic:
    return svc.set_availability(id, data)


@stock_router.patch("/{id}", response_model=ProductPublic)
def update(
    id: Annotated[int, Path(ge=1)],
    data: ProductUpdate,
    svc: ProductService = Depends(get_product_service),
):

    return svc.update(id, data)


@stock_router.get("/{id}", response_model=ProductAdminDetail)
def get_by_id_with_details(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.get_by_id_with_details(id)


@router.get("/", response_model=ProductList)
def list_all_actives(
    filters: ProductFilters = Depends(),  # para que fastapi los tome como query params y no body
    svc: ProductService = Depends(get_product_service),
):

    return svc.list_all_public(filters)


@router.get("/{id}", response_model=ProductDetail)
def get_by_id(
    id: Annotated[int, Path(ge=1)],
    svc: ProductService = Depends(get_product_service),
):
    return svc.get_active_by_id_with_details(id)


@admin_router.delete("/{id}")
def delete(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.delete(id)


@admin_router.post("/", response_model=ProductPublic, status_code=201)
def create(
    data: ProductCreate,
    svc: ProductService = Depends(get_product_service),
):
    return svc.create(data)


@admin_router.patch("/{id}/restore", response_model=ProductAdmin)
def restore(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.restore(id)


@admin_router.patch("/{id}/type", response_model=ProductAdmin)
def update_type(
    id: Annotated[int, Path(ge=1)],
    data: UpdateType,
    svc: ProductService = Depends(get_product_service),
):
    svc.update_type(id, data)


@stock_router.post("/calculate-stock", response_model=CalculateStockResponse)
def calculate_stock(
    data: CalculateStockRequest,
    svc: ProductService = Depends(get_product_service),
):
    return CalculateStockResponse(stock=svc.calculate_manufactured_stock(data))


@admin_router.patch("/{id}/ingredients")
def add_ingredients(
    id: int,
    ingredients: list[ProductIngredientBatchItem],
    svc: ProductService = Depends(get_product_service),
):
    return svc.add_ingredients(id, ingredients)
