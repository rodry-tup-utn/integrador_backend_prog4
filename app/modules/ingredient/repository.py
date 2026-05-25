from sqlmodel import Session, select, col
from sqlalchemy import func
from typing import Sequence
from datetime import datetime, timezone

from app.core.repository import BaseRepository
from app.modules.ingredient.models import Ingredient
from app.modules.ingredient.schemas import IngredientFilters

SORT_FIELDS = {"name": Ingredient.name, "created_at": Ingredient.created_at}


class IngredientRepository(BaseRepository[Ingredient]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingredient)

    def get_all_with_filters(
        self, filters: IngredientFilters, only_actives: bool = True
    ) -> Sequence[Ingredient]:
        statement = select(Ingredient)

        if only_actives:
            statement = statement.where(col(Ingredient.deleted_at).is_(None))

        if filters.search:
            statement = statement.where(
                col(Ingredient.name).ilike(f"%{filters.search}%")
            )

        if filters.is_allergen is not None:
            statement = statement.where(Ingredient.is_allergen == filters.is_allergen)

        sort_column = SORT_FIELDS.get(filters.sort_by, Ingredient.name)
        order_fn = col(sort_column).asc if filters.order == "asc" else col(sort_column).desc
        statement = statement.order_by(order_fn())

        statement = statement.offset(filters.offset).limit(filters.limit)
        return self.session.exec(statement).all()

    def count_with_filters(
        self, filters: IngredientFilters, only_actives: bool = True
    ) -> int:
        statement = select(func.count()).select_from(Ingredient)

        if only_actives:
            statement = statement.where(col(Ingredient.deleted_at).is_(None))

        if filters.search:
            statement = statement.where(
                col(Ingredient.name).ilike(f"%{filters.search}%")
            )

        if filters.is_allergen is not None:
            statement = statement.where(Ingredient.is_allergen == filters.is_allergen)

        return self.session.exec(statement).one()

    # Busca un ingrediente por su nombre exacto, si no lo encuentra devuelve None
    def get_ingredient_by_name(self, ingredient_name: str) -> Ingredient | None:
        statement = select(Ingredient).where(
            func.lower(Ingredient.name) == ingredient_name.lower()
        )

        return self.session.exec(statement).first()

    # Busca un ingrediente por ID sólo si está activo, caso contrario devuelve None
    def get_active_ingredient_by_id(self, ingredient_id: int) -> Ingredient | None:
        statement = select(Ingredient).where(
            Ingredient.id == ingredient_id, col(Ingredient.deleted_at).is_(None)
        )

        return self.session.exec(statement).first()

    def get_all_ordered(self, offset: int = 0, limit: int = 20) -> Sequence[Ingredient]:
        statement = (
            select(Ingredient)
            .order_by(func.lower(Ingredient.name))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    # Devuelve una lista paginada con todos los ingredientes activos, ordenados alfabéticamente
    def get_all_active_ingredients(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Ingredient]:
        statement = (
            select(Ingredient)
            .where(col(Ingredient.deleted_at).is_(None))
            .order_by(func.lower(Ingredient.name))
            .offset(offset)
            .limit(limit)
        )

        return self.session.exec(statement).all()

    # Devuelve la cantidad total de ingredientes activos
    def count_active_ingredients(self) -> int:
        statement = (
            select(func.count())
            .select_from(Ingredient)
            .where(col(Ingredient.deleted_at).is_(None))
        )

        return self.session.exec(statement).one()

    # Verifica que no exista un ingrediente con el mismo nombre, si existe, devuelve True
    def ingredient_name_exists(self, ingredient_name: str) -> bool:
        statement = select(Ingredient.id).where(
            func.lower(Ingredient.name) == ingredient_name.lower()
        )

        return self.session.exec(statement).first() is not None

    # Devuelve el resultado páginado de una búsqueda por coincidencias de "query" en el nombre de ingredientes activos
    def search_active_ingredients_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Ingredient]:
        statement = (
            select(Ingredient)
            .where(
                col(Ingredient.name).ilike(f"%{query}%"),
                col(Ingredient.deleted_at).is_(None),
            )
            .order_by(func.lower(Ingredient.name))
            .offset(offset)
            .limit(limit)
        )

        return self.session.exec(statement).all()

    # Devuelve la cantidad total de ingredientes que coinciden con el criterio de búsqueda
    def count_search_active_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Ingredient)
            .where(
                col(Ingredient.name).ilike(f"%{query}%"),
                col(Ingredient.deleted_at).is_(None),
            )
        )

        return self.session.exec(statement).one()

    # Devuelve el resultado paginado de una búsqueda por nombre en todos los ingredientes
    def search_ingredients_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Ingredient]:
        statement = (
            select(Ingredient)
            .where(col(Ingredient.name).ilike(f"%{query}%"))
            .order_by(func.lower(Ingredient.name))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    # Devuelve la cantidad total de ingredientes que coinciden con la bśuqeuda (incluye desactivados)
    def count_search_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Ingredient)
            .where(col(Ingredient.name).ilike(f"%{query}%"))
        )
        return self.session.exec(statement).one()

    # Método que se encarga del soft_delete de un ingrediente agregándole la fecha a la columna deleted_at
    def soft_delete_ingredient(self, ingredient: Ingredient) -> None:
        ingredient.deleted_at = datetime.now(timezone.utc)
        self.session.add(ingredient)
        self.session.flush()

    # Reactiva un ingrediente, cambiando el valor de la columna deleted_at a None
    def restore_ingredient(self, ingredient: Ingredient) -> Ingredient:
        ingredient.deleted_at = None
        self.session.add(ingredient)
        self.session.flush()
        return ingredient

    def get_active_by_ids(self, ingredients_ids: list[int]) -> Sequence[Ingredient]:
        statement = select(Ingredient).where(
            col(Ingredient.id).in_(ingredients_ids),
            col(Ingredient.deleted_at).is_(None),
        )

        return self.session.exec(statement).all()
