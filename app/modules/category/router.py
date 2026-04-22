from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.modules.category.service import CategoryService
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryPublic,
    CategoryUpdate,
)
from app.core.database import get_session


def get_category_service(session: Session = Depends(get_session)) -> CategoryService:
    return CategoryService(session)


router = APIRouter(prefix="/category", tags=["Public - Categorias"])
admin_router = APIRouter(prefix="/admin/category", tags=["Admin - Categorias"])


@router.get("/", response_model=CategoryList)
def list_all_actives(
    offset: int = 0,
    limit: int = 20,
    query: str | None = Query(default=None, max_length=50),
    svc: CategoryService = Depends(get_category_service),
):
    if query is not None:
        return svc.search(query, offset, limit)

    return svc.list_all(offset, limit)


@router.get("/search", response_model=CategoryList)
def search(
    query: str = Query(..., max_length=50),
    offset: int = 0,
    limit: int = 20,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.search(query, offset, limit)


@router.get("/{id}", response_model=CategoryPublic)
def get_by_id(
    id: int,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_by_id(id)


@router.post("/", response_model=CategoryPublic, status_code=201)
def create(
    data: CategoryCreate,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.create(data)


@router.put("/{id}", response_model=CategoryPublic)
def update(
    id: int,
    data: CategoryUpdate,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.update(id, data)


@admin_router.get("/", response_model=CategoryList)
def list_all_admin(
    offset: int = 0,
    limit: int = 20,
    query: str | None = Query(default=None, max_length=50),
    svc: CategoryService = Depends(get_category_service),
):
    if query is not None:
        return svc.search_all(query, offset, limit)

    return svc.list_all_admin(offset, limit)


@admin_router.get("/search", response_model=CategoryList)
def search_admin(
    query: str = Query(..., max_length=50),
    offset: int = 0,
    limit: int = 20,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.search_all(query, offset, limit)


@admin_router.get("/{id}", response_model=CategoryPublic)
def get_by_id_admin(
    id: int,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_by_id_admin(id)


@admin_router.delete("/{id}", status_code=204)
def delete(
    id: int,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.delete(id)


@admin_router.patch("/{id}/restore", response_model=CategoryPublic)
def restore(id: int, svc: CategoryService = Depends(get_category_service)):
    return svc.restore(id)
