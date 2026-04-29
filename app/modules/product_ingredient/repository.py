from sqlmodel import Session, select
from typing import Sequence
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.product_ingredient.models import ProductIngredient


class ProductIngredientRepository(BaseRepository[ProductIngredient]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductIngredient)

    # Busca la relación exacta entre produto e ingrediente usando la pk compuesta
    def get_by_ids(
        self, product_id: int, ingredient_id: int
    ) -> ProductIngredient | None:
        statement = select(ProductIngredient).where(
            ProductIngredient.product_id == product_id,
            ProductIngredient.ingredient_id == ingredient_id,
        )

        return self.session.exec(statement).first()

    # Devuelve todos los ingredientes asociados a un producto
    def get_ingredients_by_product(
        self, product_id: int
    ) -> Sequence[ProductIngredient]:
        statement = (
            select(ProductIngredient)
            .where(ProductIngredient.product_id == product_id)
            .options(
                joinedload(ProductIngredient.product),
                joinedload(ProductIngredient.ingredient),
            )
        )

        return self.session.exec(statement).all()

    # Devuelve todos los productos asociados a determinado ingrediente
    def get_products_by_ingredient(
        self, ingredient_id: int
    ) -> Sequence[ProductIngredient]:
        statement = select(ProductIngredient).where(
            ProductIngredient.ingredient_id == ingredient_id
        )

        return self.session.exec(statement).all()

    # Retorna true si existe ya la asociación de un producto con un ingrediente
    def exists(self, product_id: int, ingredient_id: int) -> bool:
        return self.get_by_ids(product_id, ingredient_id) is not None

    # Método de borrado físico para eliminar la relación entre producto e ingrediente
    def remove(self, relation: ProductIngredient) -> None:
        self.session.delete(relation)
        self.session.flush()
