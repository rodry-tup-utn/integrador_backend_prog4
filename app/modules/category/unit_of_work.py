from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.category.repository import CategoryRepository


class CategoriUnitOfWork(UnitOfWork["CategoriUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categorias = CategoryRepository(session)
        # Agregar productos
