from fastapi import APIRouter, Depends, Query, Path
from sqlmodel import Session
from app.modules.product.service import ProductService
from app.modules.product.schemas import (
    ProductCreate,
    ProductList,
    ProductPublic,
    ProductPublicFull,
    ProductUpdate,
    ProductAdmin,
    ProductListAdmin,
)
from app.core.database import get_session
from typing import Annotated


def get_product_service(session: Session = Depends(get_session)) -> ProductService:
    return ProductService(session)


router = APIRouter(prefix="/product", tags=["Public - Productos"])
admin_router = APIRouter(prefix="/admin/product", tags=["Admin - Product"])


@router.get("/", response_model=ProductList)
def list_all_actives(
    offset: int = 0,
    limit: int = 20,
    svc: ProductService = Depends(get_product_service),
):

    return svc.list_all(offset, limit)


@router.get("/search", response_model=ProductList)
def search(
    query: Annotated[
        str,
        Query(
            min_length=3,
            max_length=50,
            description="Se necesitan al menos 3 caracteres para hacer una busqueda",
        ),
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: ProductService = Depends(get_product_service),
):
    return svc.search_active_by_name(query, offset, limit)


@router.get("/{id}", response_model=ProductPublicFull)
def get_by_id(
    id: Annotated[int, Path(ge=1)],
    svc: ProductService = Depends(get_product_service),
):
    return svc.get_active_by_id_with_category(id)


@admin_router.delete("/{id}")
def delete(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.delete(id)


@admin_router.get("/{id}", response_model=ProductPublicFull)
def get_by_id_with_category(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.get_by_id_with_category(id)


@admin_router.patch("/{id}", response_model=ProductAdmin)
def restore(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.restore(id)


@router.post("/", response_model=ProductPublic, status_code=201)
def create(
    data: ProductCreate,
    svc: ProductService = Depends(get_product_service),
):
    return svc.create(data)


@router.get("/category/{id}", response_model=ProductList)
def list_by_category(
    id: Annotated[int, Path(ge=1)], svc: ProductService = Depends(get_product_service)
):
    return svc.get_by_category(id)


@router.patch("/{id}", response_model=ProductPublic)
def update(
    id: Annotated[int, Path(ge=1)],
    data: ProductUpdate,
    svc: ProductService = Depends(get_product_service),
):

    return svc.update(id, data)


@admin_router.get("/", response_model=ProductListAdmin)
def list_all_admin(
    svc: ProductService = Depends(get_product_service),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return svc.list_all_admin(offset, limit)
