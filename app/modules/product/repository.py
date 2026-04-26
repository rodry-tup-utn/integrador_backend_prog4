from typing import Sequence
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.product.models import Product
from sqlalchemy import func
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from app.modules.product_category.models import ProductCategoryLink


class ProductRepository(BaseRepository[Product]):
    """Repositorio de Productos"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Product)

    def get_all_active(self, offset: int = 0, limit: int = 20) -> Sequence[Product]:
        statement = (
            select(Product)
            .where(col(Product.deleted_at).is_(None))
            .order_by(func.lower(Product.name))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def count_active(self) -> int:
        statement = (
            select(func.count())
            .select_from(Product)
            .where(col(Product.deleted_at).is_(None))
        )
        return self.session.exec(statement).one()

    def get_active_by_id(self, product_id: int) -> Product | None:
        statement = (
            select(Product)
            .where(col(Product.deleted_at).is_(None))
            .where(Product.id == product_id)
        )
        return self.session.exec(statement).first()

    def get_by_id_active_with_category(self, product_id: int) -> Product | None:
        statement = (
            select(Product)
            .where(col(Product.deleted_at).is_(None))
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category_links).selectinload(
                    ProductCategoryLink.category
                )
            )
        )
        return self.session.exec(statement).first()

    def get_by_name(self, product_name: str) -> Product | None:
        statement = select(Product).where(
            func.lower(Product.name) == product_name.lower()
        )
        return self.session.exec(statement).first()

    def get_by_name_active(self, product_name: str) -> Product | None:
        statement = select(Product).where(
            func.lower(Product.name) == product_name.lower(),
            col(Product.deleted_at).is_(None),
        )
        return self.session.exec(statement).first()

    def soft_delete(self, product: Product) -> None:
        product.deleted_at = datetime.now(timezone.utc)
        product.updated_at = datetime.now(timezone.utc)
        self.session.add(product)
        self.session.flush()

    def restore(self, product: Product) -> Product:
        product.deleted_at = None
        product.updated_at = datetime.now(timezone.utc)
        self.session.add(product)
        self.session.flush()
        return product

    def search_active_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Product]:
        statement = (
            select(Product)
            .where(
                col(Product.name).ilike(f"%{query}%"),
                col(Product.deleted_at).is_(None),
            )
            .offset(offset)
            .limit(limit)
            .order_by(func.lower(Product.name))
        )
        return self.session.exec(statement).all()

    def count_search_active_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Product)
            .where(
                col(Product.name).ilike(f"%{query}%"),
                col(Product.deleted_at).is_(None),
            )
        )
        return self.session.exec(statement).one()

    def search_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Product]:
        statement = (
            select(Product)
            .where(col(Product.name).ilike(f"%{query}%"))
            .offset(offset)
            .limit(limit)
            .order_by(func.lower(Product.name))
        )
        return self.session.exec(statement).all()

    def count_search_by_name(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Product)
            .where(col(Product.name).ilike(f"%{query}%"))
        )
        return self.session.exec(statement).one()

    def list_active_by_category_id(
        self, category_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Product]:
        statement = (
            select(Product)
            .join(ProductCategoryLink)
            .where(
                ProductCategoryLink.category_id == category_id,
                col(Product.deleted_at).is_(None),
            )
            .offset(offset)
            .limit(limit)
            .order_by(func.lower(Product.name))
        )
        return self.session.exec(statement).all()

    def count_by_category(self, category_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Product)
            .join(ProductCategoryLink)
            .where(ProductCategoryLink.category_id == category_id)
        )
        return self.session.exec(statement).one()

    def get_all_active_with_categories(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Product]:
        statement = (
            select(Product)
            .where(col(Product.deleted_at).is_(None))
            .options(
                selectinload(Product.category_links).selectinload(
                    ProductCategoryLink.category
                )
            )
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()
