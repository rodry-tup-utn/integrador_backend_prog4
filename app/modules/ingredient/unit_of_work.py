from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.ingredient.repository import IngredientRepository


class IngredientUnitOfWork(UnitOfWork["IngredientUnitOfWork"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.ingredientRepo = IngredientRepository(session)
