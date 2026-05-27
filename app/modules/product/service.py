from fastapi import HTTPException, status
from app.modules.product.models import Product
from app.modules.product.schemas import (
    ProductCreate,
    ProductList,
    ProductPublic,
    ProductDetail,
    CategoryBase,
    ProductUpdate,
    ProductAdmin,
    ProductListAdmin,
    IngredientBase,
    ProductAdminDetail,
    ProductFilters,
    UpdateStock,
    UpdateAbailability,
)
from sqlmodel import Session
from app.modules.product.unit_of_work import ProductUnitOfWork
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.category.models import Category


def not_found_exception(name: str, id: int):
    raise HTTPException(
        status.HTTP_404_NOT_FOUND, f"{name.capitalize()} con id {id} no encontrado"
    )


class ProductService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_by_id(product_id)
        if not product:
            raise not_found_exception("Producto", product_id)
        return product

    def _get_active_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_active_by_id(product_id)
        if not product:
            raise not_found_exception("Producto", product_id)

        return product

    def _get_category_active_or_404(
        self, uow: ProductUnitOfWork, category_id: int
    ) -> "Category":
        category = uow.categories.get_by_id_active(category_id)
        if not category:
            raise not_found_exception("categoria", category_id)
        return category

    def _assert_name_unique(self, uow: ProductUnitOfWork, product_name: str):

        if uow.products.get_by_name(product_name):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"El producto con nombre {product_name} ya existe",
            )

    def _get_details_or_404(
        self, uow: ProductUnitOfWork, product_id: int, active_only: bool
    ) -> tuple[Product, list[CategoryBase], CategoryBase, list[IngredientBase]]:
        product = uow.products.get_by_id_with_details(
            product_id, active_only=active_only
        )
        if not product:
            raise HTTPException(404, "Producto no encontrado")

        primary_link = next(link for link in product.category_links if link.is_primary)
        primary = CategoryBase.model_validate(primary_link.category)

        categories = [
            CategoryBase.model_validate(link.category)
            for link in product.category_links
        ]
        ingredients = [
            IngredientBase(
                ingredient_id=rel.ingredient.id,
                name=rel.ingredient.name,
                description=rel.ingredient.description,
                is_removable=rel.is_removable,
                is_allergen=rel.ingredient.is_allergen,
            )
            for rel in product.ingredients
            if rel.ingredient
        ]
        return product, categories, primary, ingredients

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

    def list_all_public(self, filters: ProductFilters) -> ProductList:
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all_active(filters, True)
            total = uow.products.count_query(
                filters,
            )

            data = [ProductPublic.model_validate(p) for p in products]

            result = ProductList(data=data, total=total)

        return result

    def list_all_admin(self, filters: ProductFilters):
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all_active(filters, False)
            total = uow.products.count_query(
                filters,
            )

            data = [ProductAdmin.model_validate(p) for p in products]

            result = ProductListAdmin(data=data, total=total)

        return result

    def update(self, product_id: int, data: ProductUpdate) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)

            if data.name and data.name.lower() != product.name.lower():
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

    def delete(self, product_id: int):
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)
            uow.products.soft_delete(product)

        return status.HTTP_204_NO_CONTENT

    def restore(self, product_id: int) -> ProductAdmin:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_or_404(uow, product_id)
            if product.deleted_at is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede restaurar un producto que no está eliminado",
                )
            uow.products.restore(product)
            result = ProductAdmin.model_validate(product)
        return result

    def get_active_by_id_with_details(self, product_id: int) -> ProductDetail:
        with ProductUnitOfWork(self._session) as uow:
            product, categories, primary, ingredients = self._get_details_or_404(
                uow, product_id, active_only=True
            )
            return ProductDetail(
                **ProductPublic.model_validate(product).model_dump(),
                primary_category=primary,
                categories=categories,
                ingredients=ingredients,
            )

    def get_by_id_with_details(self, product_id: int) -> ProductAdminDetail:
        with ProductUnitOfWork(self._session) as uow:
            product, categories, primary, ingredients = self._get_details_or_404(
                uow, product_id, active_only=False
            )
            return ProductAdminDetail(
                **ProductAdmin.model_validate(product).model_dump(),
                primary_category=primary,
                categories=categories,
                ingredients=ingredients,
            )

    def update_stock(self, product_id: int, data: UpdateStock) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)
            product.stock = data.stock

            uow.products.add(product)

            result = ProductPublic.model_validate(product)

        return result

    def set_availability(
        self, product_id: int, data: UpdateAbailability
    ) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)

            if product.available != data.available:
                product.available = data.available
                uow.products.add(product)

            return ProductPublic.model_validate(product)
