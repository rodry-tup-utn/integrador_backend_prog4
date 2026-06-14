from sqlmodel import Session

from app.modules.product_ingredient.models import ProductIngredient
from app.modules.product_ingredient.schemas import (
    ProductIngredientCreate,
    ProductIngredientPublic,
    ProductIngredientUpdate,
    IngredientInProduct,
    ProductWithIngredients,
    ProductIngredientBatchCreate,
)
from app.modules.product_ingredient.unit_of_work import ProductIngredientUnitOfWork
from app.modules.product.models import ProductType
from app.core.exceptions import (
    ResourceNotFoundError,
    BusinessRuleError,
    DuplicateResourceError,
)


class ProductIngredientService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- Helpers --------------------------------------------------

    def _get_relation_or_404(
        self, uow: ProductIngredientUnitOfWork, product_id: int, ingredient_id: int
    ) -> ProductIngredient:
        relation = uow.relationRepo.get_by_ids(product_id, ingredient_id)
        if not relation:
            raise ResourceNotFoundError(
                resource="Relación producto-ingrediente",
                identifier=f"{product_id}-{ingredient_id}",
            )
        return relation

    def _get_active_product_or_404(
        self, uow: ProductIngredientUnitOfWork, product_id: int
    ):
        product = uow.productRepo.get_active_by_id(product_id)
        if not product:
            raise ResourceNotFoundError(resource="Producto", identifier=product_id)
        return product

    def _assert_ingredient_exists(
        self, uow: ProductIngredientUnitOfWork, ingredient_id: int
    ) -> None:
        if not uow.ingredientRepo.get_active_ingredient_by_id(ingredient_id):
            raise ResourceNotFoundError(
                resource="Ingrediente", identifier=ingredient_id
            )

    def _assert_product_is_manufactured(self, product) -> None:
        if product.type == ProductType.FINAL:
            raise BusinessRuleError(
                "No se pueden agregar ingredientes a un producto final",
            )

    # -- Add ingredient to product --------------------------------------------------

    def add_ingredient(
        self, product_id: int, ingredient_id: int, data: ProductIngredientCreate
    ) -> ProductIngredientPublic:
        with ProductIngredientUnitOfWork(self._session) as uow:
            product = self._get_active_product_or_404(uow, product_id)
            self._assert_product_is_manufactured(product)
            self._assert_ingredient_exists(uow, ingredient_id)

            if data.quantity_ingredient <= 0:
                raise BusinessRuleError(
                    "Un ingrediente no puede tener cantidad 0 o menor"
                )

            if uow.relationRepo.exists(product_id, ingredient_id):
                raise DuplicateResourceError(
                    resource="Relación producto-ingrediente",
                    field="ingredient_id",
                    value=ingredient_id,
                )

            relation = ProductIngredient(
                product_id=product_id,
                ingredient_id=ingredient_id,
                is_removable=data.is_removable,
                quantity_ingredient=data.quantity_ingredient,
            )

            uow.relationRepo.add(relation)
            return ProductIngredientPublic.model_validate(relation)

    # -- List ingredient of product --------------------------------------------------

    def get_product_with_ingredients(self, product_id: int) -> ProductWithIngredients:
        with ProductIngredientUnitOfWork(self._session) as uow:
            product = self._get_active_product_or_404(uow, product_id)
            relations = uow.relationRepo.get_ingredients_by_product(product_id)

            if not relations:

                return ProductWithIngredients(product_id=product.id, name=product.name, ingredients=[])  # type: ignore

            ingredients = [
                IngredientInProduct(
                    ingredient_id=rel.ingredient.id,
                    name=rel.ingredient.name,
                    description=rel.ingredient.description,
                    is_removable=rel.is_removable,
                    quantity_ingredient=rel.quantity_ingredient,
                    measurement_unit=rel.ingredient.measurement_unit,
                )
                for rel in relations
                if rel.ingredient
            ]

            first_rel = relations[0]
            return ProductWithIngredients(
                product_id=product.id,  # type: ignore
                name=first_rel.product.name,
                ingredients=ingredients,
            )

    # -- Update is_removable --------------------------------------------------

    def update_relation(
        self, product_id: int, ingredient_id: int, data: ProductIngredientUpdate
    ) -> ProductIngredientPublic:
        with ProductIngredientUnitOfWork(self._session) as uow:
            relation = self._get_relation_or_404(uow, product_id, ingredient_id)

            if data.quantity_ingredient is not None and data.quantity_ingredient <= 0:
                raise BusinessRuleError(
                    "Un ingrediente no puede tener cantidad 0 o menor"
                )

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(relation, field, value)

            uow.relationRepo.add(relation)

            return ProductIngredientPublic.model_validate(relation)

    # -- Remove ingredient from product --------------------------------------------------

    def remove_ingredient(self, product_id: int, ingredient_id: int) -> None:
        with ProductIngredientUnitOfWork(self._session) as uow:
            relation = self._get_relation_or_404(uow, product_id, ingredient_id)
            if not relation.is_removable:
                raise BusinessRuleError(
                    "No puede eliminarse un ingrediente marcado como 'no removible'",
                )
            uow.relationRepo.remove(relation)

    def add_ingredients_batch(
        self, product_id: int, data: ProductIngredientBatchCreate
    ) -> ProductWithIngredients:
        with ProductIngredientUnitOfWork(self._session) as uow:
            product = self._get_active_product_or_404(uow, product_id)
            self._assert_product_is_manufactured(product)

            ingredient_ids = [i.ingredient_id for i in data.ingredients]
            found = uow.ingredientRepo.get_active_by_ids(ingredient_ids)
            found_ids = {i.id for i in found}
            missing = set(ingredient_ids) - found_ids
            if missing:
                raise ResourceNotFoundError(
                    message=f"Ingredientes no encontrados: {missing}"
                )

            all_relations = list(
                uow.relationRepo.get_ingredients_by_product(product_id)
            )
            existing_ids = {r.ingredient_id for r in all_relations}

            new_relations = [
                ProductIngredient(
                    product_id=product_id,
                    ingredient_id=item.ingredient_id,
                    is_removable=item.is_removable,
                    quantity_ingredient=item.quantity_ingredient,
                )
                for item in data.ingredients
                if item.ingredient_id not in existing_ids
            ]

            if new_relations:
                uow.relationRepo.add_batch(new_relations)
                all_relations = list(
                    uow.relationRepo.get_ingredients_by_product(product_id)
                )

            ingredients = [
                IngredientInProduct(
                    ingredient_id=rel.ingredient.id,
                    name=rel.ingredient.name,
                    description=rel.ingredient.description,
                    is_removable=rel.is_removable,
                    quantity_ingredient=rel.quantity_ingredient,
                    measurement_unit=rel.ingredient.measurement_unit,
                )
                for rel in all_relations
                if rel.ingredient
            ]

            return ProductWithIngredients(
                product_id=product_id,
                name=product.name,  # type: ignore
                ingredients=ingredients,
            )
