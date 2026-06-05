from fastapi import APIRouter, Depends, Query, Path
from sqlmodel import Session
from typing import Annotated

from app.core.database import get_session
from app.modules.ingredient.service import IngredientService
from app.modules.ingredient.schemas import (
    IngredientCreate,
    IngredientFilters,
    IngredientList,
    IngredientPublic,
    IngredientUpdate,
    IngredientPrivate,
    IngredientListFull,
    UpdateStockIngredient,
)
from app.modules.auth.dependencies import require_role


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
    dependencies=[Depends(require_role(["ADMIN", "STOCK"]))],
)

# -- Endpoints Públicos --------------------------------------------------


@router.get("/", response_model=IngredientList)
def list_all_active_ingredients(
    filters: IngredientFilters = Depends(),
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.list_all(filters)


@router.get("/{id}", response_model=IngredientPublic)
def get_by_id(
    id: Annotated[int, Path(ge=1)],
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.get_by_id(id)


# -- Admin Endpoints --------------------------------------------------


@admin_router.get("/", response_model=IngredientListFull)
def list_all_admin(
    filters: IngredientFilters = Depends(),
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.list_all_admin(filters)


@admin_router.post("/", response_model=IngredientPublic, status_code=201)
def create(
    data: IngredientCreate, svc: IngredientService = Depends(get_ingredient_service)
):
    return svc.create_ingredient(data)


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


@admin_router.patch("/{id}/stock")
def update_stock(
    id: Annotated[int, Path(ge=1)],
    data: UpdateStockIngredient,
    svc: IngredientService = Depends(get_ingredient_service),
):
    return svc.update_stock(id, data)
