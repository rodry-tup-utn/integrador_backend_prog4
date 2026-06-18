from typing import Sequence
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.product.models import Product
from sqlalchemy import func, update, case
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from app.modules.product.schemas import ProductFilters
from app.modules.product_category.models import ProductCategoryLink
from app.modules.product_ingredient.models import ProductIngredient
from app.modules.product.models import ProductType
from app.modules.ingredient.models import Ingredient

SORT_FIELDS = {"name": Product.name, "base_price": Product.base_price}


class ProductRepository(BaseRepository[Product]):
    """Repositorio de Productos"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Product)

    def get_all_active(
        self, filters: ProductFilters, only_actives=True
    ) -> Sequence[Product]:

        statement = select(Product).offset(filters.offset).limit(filters.limit)

        if filters.search:
            statement = statement.where(col(Product.name).ilike(f"%{filters.search}%"))

        if only_actives:
            statement = statement.where(col(Product.deleted_at).is_(None))

        if filters.available:
            statement = statement.where(Product.available == True)

        if filters.type:
            statement = statement.where(Product.type == filters.type)

        if filters.category_id is not None:
            statement = statement.where(
                col(Product.id).in_(
                    select(ProductCategoryLink.product_id).where(
                        ProductCategoryLink.category_id == filters.category_id
                    )
                )
            )

        if filters.min_price is not None:
            statement = statement.where(Product.base_price >= filters.min_price)

        if filters.max_price is not None:
            statement = statement.where(Product.base_price <= filters.max_price)

        sort_column = SORT_FIELDS.get(filters.sort_by)

        if filters.order == "asc":
            statement = statement.order_by(col(sort_column).asc())
        else:
            statement = statement.order_by(col(sort_column).desc())

        return self.session.exec(statement).all()

    def count_query(self, filters: ProductFilters, only_actives: bool = True):
        statement = select(func.count()).select_from(Product)

        if only_actives:
            statement = statement.where(col(Product.deleted_at).is_(None))

        if filters.search:
            statement = statement.where(col(Product.name).ilike(f"%{filters.search}%"))

        if filters.available:
            statement = statement.where(Product.available == True)

        if filters.type:
            statement = statement.where(Product.type == filters.type)

        if filters.category_id is not None:
            statement = statement.where(
                col(Product.id).in_(
                    select(ProductCategoryLink.product_id).where(
                        ProductCategoryLink.category_id == filters.category_id
                    )
                )
            )

        if filters.min_price is not None:
            statement = statement.where(Product.base_price >= filters.min_price)

        if filters.max_price is not None:
            statement = statement.where(Product.base_price <= filters.max_price)

        return self.session.exec(statement).one()

    def get_active_by_id(self, product_id: int) -> Product | None:
        statement = (
            select(Product)
            .where(col(Product.deleted_at).is_(None))
            .where(Product.id == product_id)
        )
        return self.session.exec(statement).first()

    def get_by_id_with_details(
        self, product_id: int, active_only: bool = False
    ) -> Product | None:
        statement = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category_links).selectinload(
                    ProductCategoryLink.category
                ),
                selectinload(Product.ingredients).selectinload(
                    ProductIngredient.ingredient
                ),
            )
        )
        if active_only:
            statement = statement.where(col(Product.deleted_at).is_(None))

        return self.session.exec(statement).first()

    def get_by_name(self, product_name: str) -> Product | None:
        statement = select(Product).where(
            func.lower(Product.name) == product_name.lower()
        )
        return self.session.exec(statement).first()

    def soft_delete(self, product: Product) -> None:
        product.deleted_at = datetime.now(timezone.utc)
        product.updated_at = datetime.now(timezone.utc)
        product.available = False
        self.session.add(product)
        self.session.flush()

    def restore(self, product: Product) -> Product:
        product.deleted_at = None
        product.updated_at = datetime.now(timezone.utc)
        product.available = True
        self.session.add(product)
        self.session.flush()
        return product

    def get_by_ids(self, ids: list[int]) -> Sequence[Product]:
        statement = select(Product).where(col(Product.id).in_(ids))
        return self.session.exec(statement).all()

    def exists_active_by_id(self, product_id) -> bool:
        statement = select(Product.id).where(
            Product.id == product_id, col(Product.deleted_at).is_(None)
        )
        return self.session.exec(statement).first() is not None

    def decrease_stock_batch(self, items: list[tuple[int, int]]) -> None:
        """actualizar stock con batch, evita hacer una consulta por cada actualizacion"""
        stmt = (
            update(Product)
            .where(col(Product.id).in_([pid for pid, _ in items]))
            .where(Product.type == ProductType.FINAL)
            .values(
                stock=case(
                    *[(Product.id == pid, func.coalesce(Product.stock, 0) - qty) for pid, qty in items],  # type: ignore
                    else_=Product.stock,
                )
            )
        )
        self.session.exec(stmt)

    def increase_stock_batch(self, items: list[tuple[int, int]]) -> None:
        """igual pero sumando stock."""
        stmt = (
            update(Product)
            .where(col(Product.id).in_([pid for pid, _ in items]))
            .where(Product.type == ProductType.FINAL)
            .values(
                stock=case(
                    *[(Product.id == pid, func.coalesce(Product.stock, 0) + qty) for pid, qty in items],  # type: ignore
                    else_=Product.stock,
                )
            )
        )
        self.session.exec(stmt)

    def get_final_product_ids(self, ids: list[int]) -> set[int]:
        stmt = select(Product.id).where(
            col(Product.id).in_(ids),
            Product.type == ProductType.FINAL,
        )
        return set(self.session.exec(stmt).all())

    def get_manufactured_stocks_batch(self, product_ids: list[int]) -> dict[int, int]:
        if not product_ids:
            return {}

        stmt = (
            select(
                ProductIngredient.product_id,
                ProductIngredient.quantity_ingredient,
                Ingredient.stock,
                col(Ingredient.id).label("ingredient_id"),
            )
            .outerjoin(Ingredient, Ingredient.id == ProductIngredient.ingredient_id)
            .where(col(ProductIngredient.product_id).in_(product_ids))
        )
        rows = self.session.exec(stmt).all()

        groups: dict[int, list] = {}
        for row in rows:
            groups.setdefault(row.product_id, []).append(row)

        result: dict[int, int] = {}
        for pid, items in groups.items():
            min_val: int | None = None
            for item in items:
                if (
                    item.ingredient_id is None
                    or item.stock is None
                    or item.quantity_ingredient == 0
                ):
                    min_val = 0
                    break
                stock_val = int(item.stock // item.quantity_ingredient)
                min_val = stock_val if min_val is None else min(min_val, stock_val)
            result[pid] = min_val or 0

        return result
