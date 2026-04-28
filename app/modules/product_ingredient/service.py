from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.product_ingredient.models import ProductIngredient
from app.modules.product_ingredient.schemas import (
    ProductIngredientCreate,
    ProductIngredientPublic,
    ProductIngredientUpdate,
    IngredientInProduct,
    ProductWithIngredients,
)
from app.modules.product_ingredient.unit_of_work import ProductIngredientUnitOfWork


class ProductIngredientService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- Helpers --------------------------------------------------

    def _get_relation_or_404(
        self, uow: ProductIngredientUnitOfWork, product_id: int, ingredient_id: int
    ) -> ProductIngredient:
        relation = uow.relationRepo.get_by_ids(product_id, ingredient_id)
        if not relation:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"El ingrediente con id: {ingredient_id} no está asociado con el producto con id: {product_id}",
            )
        return relation

    # Verifica que el producto exista y esté activo
    def _assert_product_exists(
        self, uow: ProductIngredientUnitOfWork, product_id: int
    ) -> None:
        if not uow.productRepo.get_active_by_id(product_id):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Producto con id: {product_id} no encontrado",
            )

    # Verifica que el ingrediente exista y esté activo
    def _assert_ingredient_exists(
        self, uow: ProductIngredientUnitOfWork, ingredient_id: int
    ) -> None:
        if not uow.ingredientRepo.get_active_ingredient_by_id(ingredient_id):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Ingrediente con id: {ingredient_id} no encontrado",
            )

    # -- Add ingredient to product --------------------------------------------------

    def add_ingredient(
        self, product_id: int, ingredient_id: int, data: ProductIngredientCreate
    ) -> ProductIngredientPublic:
        with ProductIngredientUnitOfWork(self._session) as uow:
            self._assert_product_exists(uow, product_id)
            self._assert_ingredient_exists(uow, ingredient_id)

            if uow.relationRepo.exists(product_id, ingredient_id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El ingrediente con id: {ingredient_id} ya está asociado al producto con id: {product_id}",
                )

            relation = ProductIngredient(
                product_id=product_id,
                ingredient_id=ingredient_id,
                is_removable=data.is_removable,
            )

            uow.relationRepo.add(relation)
            return ProductIngredientPublic.model_validate(relation)

    # -- List ingredient of product --------------------------------------------------

    def get_product_with_ingredients(self, product_id: int) -> ProductWithIngredients:
        with ProductIngredientUnitOfWork(self._session) as uow:
            self._assert_product_exists(uow, product_id)
            product = uow.productRepo.get_active_by_id(product_id)
            relations = uow.relationRepo.get_ingredients_by_product(product_id)

            ingredients = []
            for rel in relations:
                ingredient = uow.ingredientRepo.get_by_id(rel.ingredient_id)
                if ingredient:
                    ingredients.append(
                        IngredientInProduct(
                            ingredient_id=ingredient.id,
                            name=ingredient.name,
                            description=ingredient.description,
                            is_removable=rel.is_removable,
                        )
                    )

            return ProductWithIngredients(
                product_id=product.id, name=product.name, ingredients=ingredients  # type: ignore
            )

    # -- Update is_removable --------------------------------------------------

    def update_relation(
        self, product_id: int, ingredient_id: int, data: ProductIngredientUpdate
    ) -> ProductIngredientPublic:
        with ProductIngredientUnitOfWork(self._session) as uow:
            relation = self._get_relation_or_404(uow, product_id, ingredient_id)
            relation.is_removable = data.is_removable
            uow.relationRepo.add(relation)
            return ProductIngredientPublic.model_validate(relation)

    # -- Remove ingredient from product --------------------------------------------------

    def remove_ingredient(self, product_id: int, ingredient_id: int) -> None:
        with ProductIngredientUnitOfWork(self._session) as uow:
            relation = self._get_relation_or_404(uow, product_id, ingredient_id)
            if not relation.is_removable:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "No puede eliminarse un ingrediente marcado como 'no removible'",
                )
            uow.relationRepo.remove(relation)
