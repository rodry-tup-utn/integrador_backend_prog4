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

    def _build_category_map(
        self, categories: list["Category"]
    ) -> dict[int, "Category"]:
        return {c.id: c for c in categories if c.id is not None}

    def _build_parent_chain(
        self,
        category: "Category",
        category_map: dict[int, "Category"],
    ) -> list[int]:

        result: list[int] = []
        visited: set[int] = set()

        current = category

        while current is not None:
            if current.id in visited:
                raise ValueError("Ciclo detectado en categorias")

            visited.add(current.id)  # type: ignore
            result.append(current.id)  # type: ignore

            if current.parent_id is None:
                break

            current = category_map.get(current.parent_id)

        return result

    def create(self, data: ProductCreate) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)
            primary_category = self._get_category_active_or_404(uow, data.category_id)
            product = Product.model_validate(data)
            uow.products.add(product)

            categories = list(uow.categories.get_all_active_no_paged())
            category_map = self._build_category_map(categories)
            chain_ids = self._build_parent_chain(primary_category, category_map)

            uow.product_category_link.create_chain(
                product.id, chain_ids, data.category_id  # type: ignore
            )

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
            categories = [
                CategoryBase.model_validate(link.category)
                for link in product.category_links
            ]
            primary = next(
                (
                    CategoryBase.model_validate(link.category)
                    for link in product.category_links
                    if link.is_primary
                )
            )

            result = ProductPublicFull(
                id=product.id,  # type:ignore
                name=product.name,
                base_price=product.base_price,
                description=product.description,
                created_at=product.created_at,
                images_url=product.images_url,
                updated_at=product.updated_at,
                deleted_at=product.deleted_at,
                primary_category=primary,
                categories=categories,
            )
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

            current_primary = uow.product_category_link.get_primary_by_product_id(
                product_id
            )

            if data.category_id is not None:
                new_category = self._get_category_active_or_404(uow, data.category_id)

                if (
                    not current_primary
                    or current_primary.category_id != new_category.id
                ):
                    uow.product_category_link.delete_by_product_id(product_id)

                    categories = list(uow.categories.get_all_active_no_paged())
                    category_map = self._build_category_map(categories)
                    chain_ids = self._build_parent_chain(new_category, category_map)

                    uow.product_category_link.create_chain(
                        product_id, chain_ids, new_category.id  # type: ignore
                    )

            patch = data.model_dump(exclude_unset=True, exclude={"category_id"})
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

    def delete(self, product_id: int):
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)
            uow.products.soft_delete(product)

        return status.HTTP_204_NO_CONTENT

    def restore(self, product_id: int) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_or_404(uow, product_id)
            if product.deleted_at is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede restaurar un producto que no está eliminado",
                )
            uow.products.restore(product)
            result = ProductPublic.model_validate(product)
        return result

    def get_by_category(
        self, category_id: int, offset: int = 0, limit: int = 20
    ) -> ProductList:
        with ProductUnitOfWork(self._session) as uow:
            self._get_category_active_or_404(uow, category_id)
            products = uow.products.list_active_by_category_id(
                category_id, offset, limit
            )
            data = [ProductPublic.model_validate(p) for p in products]
            count = uow.products.count_by_category(category_id)

            result = ProductList(data=data, total=count)
        return result
