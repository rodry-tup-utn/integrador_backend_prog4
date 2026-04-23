from fastapi import APIRouter, Depends, Query, Path
from sqlmodel import Session
from app.modules.category.service import CategoryService
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryPublic,
    CategoryUpdate,
)
from app.core.database import get_session
from typing import Annotated


def get_category_service(session: Session = Depends(get_session)) -> CategoryService:
    return CategoryService(session)


router = APIRouter(prefix="/category", tags=["Public - Categorias"])
admin_router = APIRouter(prefix="/admin/category", tags=["Admin - Categorias"])


@router.get("/", response_model=CategoryList)
def list_all_actives(
    offset: int = 0,
    limit: int = 20,
    svc: CategoryService = Depends(get_category_service),
):

    return svc.list_all(offset, limit)


@router.get("/search", response_model=CategoryList)
def search(
    query: Annotated[str, Query(min_length=1, max_length=50)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.search(query, offset, limit)


@router.get("/{id}", response_model=CategoryPublic)
def get_by_id(
    id: Annotated[int, Path(ge=1)],
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_by_id(id)


@router.post("/", response_model=CategoryPublic, status_code=201)
def create(
    data: CategoryCreate,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.create(data)


@router.patch("/{id}", response_model=CategoryPublic)
def update(
    id: Annotated[int, Path(ge=1)],
    data: CategoryUpdate,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.update(id, data)


@admin_router.get("/", response_model=CategoryList)
def list_all_admin(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.list_all_admin(offset, limit)


@admin_router.get("/search", response_model=CategoryList)
def search_admin(
    query: Annotated[str, Query(max_length=50, min_length=3)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.search_all(query, offset, limit)


@admin_router.get("/{id}", response_model=CategoryPublic)
def get_by_id_admin(
    id: Annotated[int, Path(ge=1)],
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_by_id_admin(id)


@admin_router.patch("/{id}/restore", response_model=CategoryPublic)
def restore(
    id: Annotated[int, Path(ge=1)], svc: CategoryService = Depends(get_category_service)
):
    return svc.restore(id)


@admin_router.delete("/{id}", status_code=204)
def delete(
    id: Annotated[int, Path(ge=1)],
    svc: CategoryService = Depends(get_category_service),
):
    return svc.delete(id)
