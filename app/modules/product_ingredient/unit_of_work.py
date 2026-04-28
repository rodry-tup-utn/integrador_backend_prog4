from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.product_ingredient.repository import ProductIngredientRepository
from app.modules.product.repository import ProductRepository
from app.modules.ingredient.repository import IngredientRepository


class ProductIngredientUnitOfWork(UnitOfWork["ProductIngredientUnitOfWork"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.relationRepo = ProductIngredientRepository(session)
        self.productRepo = ProductRepository(session)
        self.ingredientRepo = IngredientRepository(session)
