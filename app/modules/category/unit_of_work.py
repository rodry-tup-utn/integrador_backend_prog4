from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.category.repository import CategoryRepository
from app.modules.product_category.repository import ProductCategoryLinkRepository


class CategoryUnitOfWork(UnitOfWork["CategoryUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categories = CategoryRepository(session)
        self.category_products = ProductCategoryLinkRepository(session)
