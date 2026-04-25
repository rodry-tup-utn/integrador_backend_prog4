from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.product.repository import ProductRepository
from app.modules.category.repository import CategoryRepository


class ProductUnitOfWork(UnitOfWork["ProductUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)
