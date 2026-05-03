from fastapi import APIRouter, Depends, Query, Path
from sqlmodel import Session
from typing import Annotated

from app.core.database import get_session
from app.modules.ingredient.service import IngredientService
from app.modules.ingredient.schemas import (
    IngredientCreate,
    IngredientList,
    IngredientPublic,
    IngredientUpdate,
    IngredientPrivate,
)
from app.modules.auth.dependencies import get_current_admin_user


def get_ingredient_service(
    session: Session = Depends(get_session),
) -> IngredientService:
    return IngredientService(session)


router = APIRouter(
    prefix="/ingredient",
    tags=["Public - Ingredientes"],
)
admin_router = APIRouter(
    prefix="/admin/ingredient",
    tags=["Admin - Ingredientes"],
    dependencies=[Depends(get_current_admin_user)],
)

# -- Endpoints Públicos --------------------------------------------------


@router.get("/", response_model=IngredientList)
def list_all_active_ingredients(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.list_all(offset, limit)


@router.get("/search", response_model=IngredientList)
def search(
    query: Annotated[str, Query(min_length=1, max_length=50)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.search_ingredient(query, offset, limit)


@router.get("/{id}", response_model=IngredientPublic)
def get_by_id(
    id: Annotated[int, Path(ge=1)],
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.get_by_id(id)


# -- Admin Endpoints --------------------------------------------------


@admin_router.get("/", response_model=IngredientList)
def list_all_admin(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.list_all_admin(offset, limit)


@admin_router.post("/", response_model=IngredientPublic, status_code=201)
def create(
    data: IngredientCreate, svc: IngredientService = Depends(get_ingredient_service)
):
    return svc.create_ingredient(data)


@admin_router.get("/search", response_model=IngredientList)
def search_admin(
    query: Annotated[str, Query(min_length=1, max_length=50)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.search_ingredient_admin(query, offset, limit)


@admin_router.get("/{id}", response_model=IngredientPrivate)
def get_by_id_admin(
    id: Annotated[int, Path(ge=1)],
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.get_by_id_admin(id)


@admin_router.patch("/{id}", response_model=IngredientPrivate)
def update(
    id: Annotated[int, Path(ge=1)],
    data: IngredientUpdate,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.update_ingredient(id, data)


@admin_router.patch("/{id}/restore", response_model=IngredientPrivate)
def restore(
    id: Annotated[int, Path(ge=1)],
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.restore_deleted_ingredient(id)


@admin_router.delete("/{id}", status_code=204)
def delete(
    id: Annotated[int, Path(ge=1)],
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.delete_ingredient(id)
