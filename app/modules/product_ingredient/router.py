from fastapi import APIRouter, Depends, Path
from sqlmodel import Session
from typing import Annotated

from app.core.database import get_session
from app.modules.product_ingredient.service import ProductIngredientService
from app.modules.product_ingredient.schemas import (
    ProductIngredientCreate,
    ProductIngredientPublic,
    ProductIngredientUpdate,
    ProductWithIngredients,
)


def get_service(session: Session = Depends(get_session)) -> ProductIngredientService:
    return ProductIngredientService(session)


router = APIRouter(
    prefix="/product/{product_id}/ingredient", tags=["Public - Producto Ingredientes"]
)


@router.get("/", response_model=ProductWithIngredients)
def get_product_with_ingredients(
    product_id: Annotated[int, Path(ge=1)],
    svc: ProductIngredientService = Depends(get_service),
):
    return svc.get_product_with_ingredients(product_id)


@router.post(
    "/{ingredient_id}", response_model=ProductIngredientPublic, status_code=201
)
def add_ingredient(
    product_id: Annotated[int, Path(ge=1)],
    ingredient_id: Annotated[int, Path(ge=1)],
    data: ProductIngredientCreate,
    svc: ProductIngredientService = Depends(get_service),
):
    return svc.add_ingredient(product_id, ingredient_id, data)


@router.patch("/{ingredient_id}", response_model=ProductIngredientPublic)
def update_ingredient(
    product_id: Annotated[int, Path(ge=1)],
    ingredient_id: Annotated[int, Path(ge=1)],
    data: ProductIngredientUpdate,
    svc: ProductIngredientService = Depends(get_service),
):
    return svc.update_relation(product_id, ingredient_id, data)


@router.delete("/{ingredient_id}", status_code=204)
def remove_ingredient(
    product_id: Annotated[int, Path(ge=1)],
    ingredient_id: Annotated[int, Path(ge=1)],
    svc: ProductIngredientService = Depends(get_service),
):
    return svc.remove_ingredient(product_id, ingredient_id)
