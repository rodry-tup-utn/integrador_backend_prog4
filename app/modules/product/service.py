from fastapi import HTTPException, status
from app.modules.product.models import Product
from app.modules.product.schemas import (
    ProductCreate,
    ProductList,
    ProductPublic,
    ProductPublicFull,
    CategoryBase,
    ProductUpdate,
)
from sqlmodel import Session
from app.modules.product.unit_of_work import ProductUnitOfWork
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.modules.product.models import Category


class ProductService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Producto con id {product_id} no encontrado",
            )
        return product

    def _get_active_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_active_by_id(product_id)
        if not product:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Producto con id {product_id} no encontrado",
            )
        return product

    def _get_active_with_category_or_404(
        self, uow: ProductUnitOfWork, product_id: int
    ) -> Product:
        product = uow.products.get_by_id_active_with_category(product_id)
        if not product:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Producto con id {product_id} no encontrado",
            )
        return product

    def _get_category_active_or_404(
        self, uow: ProductUnitOfWork, category_id: int
    ) -> "Category":
        category = uow.categories.get_by_id_active(category_id)
        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Categoria id {category_id} no econtrada"
            )
        return category

    def _assert_name_unique(self, uow: ProductUnitOfWork, product_name: str):

        if uow.products.get_by_name(product_name):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"El producto con nombre {product_name} ya existe",
            )

    def create(self, data: ProductCreate) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)
            self._get_category_active_or_404(uow, data.category_id)
            product = Product.model_validate(data)
            uow.products.add(product)

            result = ProductPublic.model_validate(product)
        return result

    def get_by_id(self, product_id: int) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)
            result = ProductPublic.model_validate(product)
        return result

    def get_by_id_admin(self, product_id: int) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_or_404(uow, product_id)
            result = ProductPublic.model_validate(product)
        return result

    def get_by_id_with_category(self, product_id: int) -> ProductPublicFull:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_with_category_or_404(uow, product_id)
            result = ProductPublicFull.model_validate(product)
        return result

    def list_all(self, offset: int = 0, limit: int = 20) -> ProductList:
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all_active(offset, limit)
            total = uow.products.count_active()

            data = [ProductPublic.model_validate(c) for c in products]
            result = ProductList(data=data, total=total)

        return result

    def list_all_admin(self, offset: int = 0, limit: int = 20) -> ProductList:
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all(offset, limit)
            total = uow.products.count()

            data = [ProductPublic.model_validate(p) for p in products]
            result = ProductList(data=data, total=total)
        return result

    def update(self, product_id: int, data: ProductUpdate) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)

            if data.name and data.name != product.name:
                self._assert_name_unique(uow, data.name)

            if data.category_id is not None:
                self._get_category_active_or_404(uow, data.category_id)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(product, field, value)

            product.updated_at = datetime.now(timezone.utc)
            uow.products.add(product)

            result = ProductPublic.model_validate(product)
        return result

    def search_active_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> ProductList:
        query = query.strip()
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.search_active_by_name(query, offset, limit)
            count = uow.products.count_search_active_by_name(query)

            result = [ProductPublic.model_validate(p) for p in products]

        return ProductList(data=result, total=count)

    def search_all_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> ProductList:
        query = query.strip()
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.search_by_name(query, offset, limit)
            count = uow.products.count_search_by_name(query)

            result = [ProductPublic.model_validate(p) for p in products]

        return ProductList(data=result, total=count)
