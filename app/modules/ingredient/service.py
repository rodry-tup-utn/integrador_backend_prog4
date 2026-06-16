from sqlmodel import Session, select
from datetime import datetime, timezone

from app.modules.ingredient.models import Ingredient, MeasurementUnit
from app.modules.ingredient.schemas import (
    IngredientCreate,
    IngredientFilters,
    IngredientList,
    IngredientPublic,
    IngredientUpdate,
    IngredientPrivate,
    IngredientListFull,
    MeasurementUnitPublic,
    UpdateStockIngredient,
)
from app.core.exceptions import (
    ResourceNotFoundError,
    BusinessRuleError,
    DuplicateResourceError,
)
from app.modules.ingredient.unit_of_work import IngredientUnitOfWork


class IngredientService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- Helpers --------------------------------------------------

    def _get_or_404(self, uow: IngredientUnitOfWork, ingredient_id: int) -> Ingredient:
        ingredient = uow.ingredientRepo.get_by_id(ingredient_id)

        if not ingredient:
            raise ResourceNotFoundError(
                resource="Ingrediente", identifier=ingredient_id
            )
        return ingredient

    def _get_active_or_404(
        self, uow: IngredientUnitOfWork, ingredient_id: int
    ) -> Ingredient:
        ingredient = uow.ingredientRepo.get_active_ingredient_by_id(ingredient_id)

        if not ingredient:
            raise ResourceNotFoundError(
                resource="Ingrediente", identifier=ingredient_id
            )
        return ingredient

    def _assert_name_unique(
        self, uow: IngredientUnitOfWork, ingredient_name: str
    ) -> None:
        if uow.ingredientRepo.ingredient_name_exists(ingredient_name):
            raise DuplicateResourceError(
                resource="Ingrediente", field="nombre", value=ingredient_name
            )

    # -- Measurement Units --------------------------------------------------

    def list_measurement_units(self) -> list[MeasurementUnitPublic]:
        units = self._session.exec(select(MeasurementUnit)).all()
        return [MeasurementUnitPublic.model_validate(u) for u in units]

    # -- Create --------------------------------------------------

    def create_ingredient(self, data: IngredientCreate) -> IngredientPrivate:
        with IngredientUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)
            ingredient = Ingredient.model_validate(data)
            uow.ingredientRepo.add(ingredient)
            return IngredientPrivate.model_validate(ingredient)

    # -- Get by id --------------------------------------------------

    def get_by_id(self, ingredient_id: int) -> IngredientPublic:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_active_or_404(uow, ingredient_id)
            return IngredientPublic.model_validate(ingredient)

    def get_by_id_admin(self, ingredient_id: int) -> IngredientPrivate:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_or_404(uow, ingredient_id)
            return IngredientPrivate.model_validate(ingredient)

    # -- List --------------------------------------------------

    def list_all(self, filters: IngredientFilters) -> IngredientList:
        with IngredientUnitOfWork(self._session) as uow:
            ingredients = uow.ingredientRepo.get_all_with_filters(
                filters, only_actives=True
            )
            total = uow.ingredientRepo.count_with_filters(filters, only_actives=True)
            data = [IngredientPublic.model_validate(i) for i in ingredients]
            return IngredientList(data=data, total=total)

    def list_all_admin(self, filters: IngredientFilters) -> IngredientListFull:
        with IngredientUnitOfWork(self._session) as uow:
            ingredients = uow.ingredientRepo.get_all_with_filters(
                filters, only_actives=False
            )
            total = uow.ingredientRepo.count_with_filters(filters, only_actives=False)
            data = [IngredientPrivate.model_validate(i) for i in ingredients]
            return IngredientListFull(data=data, total=total)

    # -- Update --------------------------------------------------

    def update_ingredient(
        self, ingredient_id: int, data: IngredientUpdate
    ) -> IngredientPrivate:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_active_or_404(uow, ingredient_id)

            if data.name and data.name.lower() != ingredient.name.lower():
                self._assert_name_unique(uow, data.name)

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(ingredient, field, value)

            ingredient.updated_at = datetime.now(timezone.utc)
            uow.ingredientRepo.add(ingredient)
            return IngredientPrivate.model_validate(ingredient)

    # -- Delete --------------------------------------------------

    def delete_ingredient(self, ingredient_id: int) -> None:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_active_or_404(uow, ingredient_id)

            if uow.product_ingredient.ingredient_has_products(ingredient_id):
                raise BusinessRuleError(
                    "El ingrediente no puede eliminarse ya que se encuentra vinculado a uno o mas productos"
                )

            uow.ingredientRepo.soft_delete_ingredient(ingredient)

    # -- Restore --------------------------------------------------

    def restore_deleted_ingredient(self, ingredient_id: int) -> IngredientPrivate:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_or_404(uow, ingredient_id)

            if ingredient.deleted_at is None:
                raise BusinessRuleError("El ingrediente no está eliminado")

            uow.ingredientRepo.restore_ingredient(ingredient)
            return IngredientPrivate.model_validate(ingredient)

    def update_stock(
        self, ingredient_id: int, data: UpdateStockIngredient
    ) -> IngredientPrivate:
        with IngredientUnitOfWork(self._session) as uow:
            ingredient = self._get_or_404(uow, ingredient_id)

            now = datetime.now(timezone.utc)
            ingredient.stock = data.stock
            ingredient.updated_at = now

            uow.ingredientRepo.add(ingredient)

            return IngredientPrivate.model_validate(ingredient)
