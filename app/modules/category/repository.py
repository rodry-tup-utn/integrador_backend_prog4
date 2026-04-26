from typing import Sequence
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.category.models import Category
from sqlalchemy import func
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload


class CategoryRepository(BaseRepository[Category]):
    """Repositorio de Categorias"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Category)

    def get_by_name(self, category_name: str) -> Category | None:
        statement = select(Category).where(Category.name == category_name)
        return self.session.exec(statement).first()

    def get_by_name_active(self, category_name: str) -> Category | None:
        statement = select(Category).where(
            func.lower(Category.name) == category_name.lower(),
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

    def get_all_active_no_paged(self) -> Sequence[Category]:
        statement = select(Category).where(col(Category.deleted_at).is_(None))
        return self.session.exec(statement).all()

    def get_all_root_active(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Category]:
        statement = (
            select(Category)
            .where(col(Category.deleted_at).is_(None))
            .where(col(Category.parent_id).is_(None))
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
            .options(selectinload(Category.children))
        )
        return self.session.exec(statement).first()

    def get_by_id_active_with_children(self, category_id: int) -> Category | None:
        statement = (
            select(Category)
            .where(col(Category.deleted_at).is_(None))
            .where(Category.id == category_id)
            .options(selectinload(Category.children))
        )
        return self.session.exec(statement).first()

    def get_children_active(self, category_id: int) -> list[Category]:
        statement = (
            select(Category)
            .where(Category.id == category_id)
            .where(col(Category.deleted_at).is_(None))
            .options(selectinload(Category.children))
        )

        category = self.session.exec(statement).first()

        if not category:
            return []

        return category.children

    def exists_by_name(self, category_name: str) -> bool:
        statement = select(Category.id).where(
            func.lower(Category.name) == category_name.lower()
        )
        return self.session.exec(statement).first() is not None

    def count_active(self) -> int:
        statement = (
            select(func.count())
            .select_from(Category)
            .where(col(Category.deleted_at).is_(None))
        )
        return self.session.exec(statement).one()

    def count_root_active(self) -> int:
        statement = (
            select(func.count())
            .select_from(Category)
            .where(col(Category.deleted_at).is_(None))
            .where(col(Category.parent_id).is_(None))
        )
        return self.session.exec(statement).one()

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
        category.updated_at = datetime.now(timezone.utc)

        self.session.add(category)
        self.session.flush()

    def restore(self, category: Category) -> Category:
        category.deleted_at = None
        category.updated_at = datetime.now(timezone.utc)
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

    def has_children_active(self, category_id: int) -> bool:
        statement = select(Category.id).where(
            Category.parent_id == category_id, col(Category.deleted_at).is_(None)
        )
        return self.session.exec(statement).first() is not None
