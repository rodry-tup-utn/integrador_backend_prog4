from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.product.repository import ProductRepository
from app.modules.category.repository import CategoryRepository
from app.modules.product_category.repository import ProductCategoryLinkRepository
from app.modules.product_ingredient.repository import ProductIngredientRepository
from app.modules.ingredient.repository import IngredientRepository


class ProductUnitOfWork(UnitOfWork["ProductUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)
        self.product_category_link = ProductCategoryLinkRepository(session)
        self.product_ingredient = ProductIngredientRepository(session)
        self.ingredients = IngredientRepository(session)
