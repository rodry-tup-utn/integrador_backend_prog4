from typing import Sequence
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.category.models import Category
from sqlalchemy import func
from datetime import datetime, timezone


class CategoryRepository(BaseRepository[Category]):
    """Repositorio de Categorias"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Category)

    def get_by_name(self, category_name: str) -> Category | None:
        statement = select(Category).where(Category.name == category_name)
        return self.session.exec(statement).first()

    def get_by_name_active(self, category_name: str) -> Category | None:
        statement = select(Category).where(
            func.lower(Category.name) == category_name,
            col(Category.deleted_at).is_(None),
        )
        return self.session.exec(statement).first()

    def get_all_active(self, offset: int = 0, limit: int = 20) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(col(Category.deleted_at).is_(None))
            .order_by(func.lower(Category.name))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def get_by_id_active(self, category_id: int) -> Category | None:
        statement = (
            select(Category)
            .where(col(Category.deleted_at).is_(None))
            .where(Category.id == category_id)
        )
        return self.session.exec(statement).first()

    def exists_by_name(self, category_name: str) -> bool:
        statement = select(Category.id).where(
            func.lower(Category.name) == category_name.lower()
        )
        return self.session.exec(statement).first() is not None

    def exists_by_name_active(self, category_name: str) -> bool:
        statement = select(Category.id).where(
            func.lower(Category.name) == category_name.lower(),
            col(Category.deleted_at).is_(None),
        )
        return self.session.exec(statement).first() is not None

    def count_active(self) -> int:
        statement = (
            select(func.count())
            .select_from(Category)
            .where(col(Category.deleted_at).is_(None))
        )
        return self.session.exec(statement).one()

    def get_children(self, parent_id: int) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(Category.parent_id == parent_id, col(Category.deleted_at).is_(None))
            .order_by(func.lower(Category.name))
        )
        return self.session.exec(statement).all()

    def get_root_categories(self) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(
                col(Category.parent_id).is_(None), col(Category.deleted_at).is_(None)
            )
            .order_by(func.lower(Category.name))
        )
        return self.session.exec(statement).all()

    def soft_delete(self, category: Category) -> None:
        category.deleted_at = datetime.now(timezone.utc)
        self.session.add(category)
        self.session.flush()

    def restore(self, category: Category) -> Category:
        category.deleted_at = None
        self.session.add(category)
        self.session.flush()
        return category

    def search_active_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(
                col(Category.name).ilike(f"%{query}%"),
                col(Category.deleted_at).is_(None),
            )
            .offset(offset)
            .limit(limit)
            .order_by(func.lower(Category.name))
        )
        return self.session.exec(statement).all()

    def count_search_active_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Category)
            .where(
                col(Category.name).ilike(f"%{query}%"),
                col(Category.deleted_at).is_(None),
            )
        )
        return self.session.exec(statement).one()

    def search_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(col(Category.name).ilike(f"%{query}%"))
            .offset(offset)
            .limit(limit)
            .order_by(func.lower(Category.name))
        )
        return self.session.exec(statement).all()

    def count_search_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Category)
            .where(col(Category.name).ilike(f"%{query}%"))
        )
        return self.session.exec(statement).one()
