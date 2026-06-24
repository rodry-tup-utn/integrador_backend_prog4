from fastapi import status
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
    UpdateType,
)
from app.modules.ingredient.models import MeasurementUnit
from app.modules.product_ingredient.models import ProductIngredient
from app.modules.product_ingredient.schemas import ProductIngredientBatchItem
from app.modules.product.schemas import CalculateStockRequest
from app.core.exceptions import (
    DuplicateResourceError,
    BusinessRuleError,
    ResourceNotFoundError,
)
from sqlmodel import Session, select
from app.modules.product.unit_of_work import ProductUnitOfWork
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from app.modules.product.models import ProductType

if TYPE_CHECKING:
    from app.modules.category.models import Category


class ProductService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_by_id(product_id)
        if not product:
            raise ResourceNotFoundError(resource="Producto", identifier=product_id)
        return product

    def _get_active_or_404(self, uow: ProductUnitOfWork, product_id: int) -> Product:
        product = uow.products.get_active_by_id(product_id)
        if not product:
            raise ResourceNotFoundError(resource="Producto", identifier=product_id)

        return product

    def _get_category_active_or_404(
        self, uow: ProductUnitOfWork, category_id: int
    ) -> "Category":
        category = uow.categories.get_by_id_active(category_id)
        if not category:
            raise ResourceNotFoundError(resource="Categoria", identifier=category_id)
        return category

    def _assert_name_unique(self, uow: ProductUnitOfWork, product_name: str):

        if uow.products.get_by_name(product_name):
            raise DuplicateResourceError(
                resource="Producto", field="nombre", value=product_name
            )

    def _assert_sales_unit_exists(self, sales_unit: str) -> None:
        stmt = select(MeasurementUnit).where(MeasurementUnit.code == sales_unit)
        unit = self._session.exec(stmt).first()
        if not unit:
            raise ResourceNotFoundError(
                resource="Unidad de medida", identifier=sales_unit
            )

    def _get_details_or_404(
        self, uow: ProductUnitOfWork, product_id: int, active_only: bool
    ) -> tuple[Product, list[CategoryBase], CategoryBase, list[IngredientBase]]:
        product = uow.products.get_by_id_with_details(
            product_id, active_only=active_only
        )
        if not product:
            raise ResourceNotFoundError(resource="Producto", identifier=product_id)

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
                quantity=rel.quantity_ingredient,
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
                raise BusinessRuleError(message="Ciclo detectado en categorias")

            visited.add(current.id)  # type: ignore
            result.append(current.id)  # type: ignore

            if current.parent_id is None:
                break

            current = category_map.get(current.parent_id)

        return result

    def _add_ingredients(
        self,
        uow: ProductUnitOfWork,
        product: Product,
        ingredients_data: list[ProductIngredientBatchItem],
    ) -> None:

        self._assert_manufactured_product(
            product, "Un producto final no puede tener ingredientes"
        )

        if not ingredients_data:
            raise BusinessRuleError(
                message="Un producto manufacturado debe tener al menos 1 ingrediente",
            )

        # validacion de ingrediente con cantidad 0
        for ingredient in ingredients_data:
            if ingredient.quantity_ingredient <= 0:
                raise BusinessRuleError(
                    "Un ingrediente no puede tener cantidad 0 o menor"
                )

        found = uow.ingredients.get_active_by_ids(
            [i.ingredient_id for i in ingredients_data]
        )
        found_ids = {i.id for i in found}
        missing = set(i.ingredient_id for i in ingredients_data) - found_ids
        if missing:
            raise BusinessRuleError(
                message=f"Ingredientes no encontrados: {sorted(missing)}"
            )

        relations = [
            ProductIngredient(
                product_id=product.id,  # type: ignore
                ingredient_id=item.ingredient_id,
                is_removable=item.is_removable,
                quantity_ingredient=item.quantity_ingredient,
            )
            for item in ingredients_data
        ]
        uow.product_ingredient.add_batch(relations)

    def _assert_manufactured_product(
        self,
        product: Product,
        error_message: str = "El producto no es de tipo Manufacturado",
    ):
        if product.type == ProductType.FINAL:
            raise BusinessRuleError(
                message=error_message,
            )

        # calcular stock por ingredientes o retornar product.stock en productos finales

    def _get_product_stock(self, uow: ProductUnitOfWork, product_id: int) -> int:
        product = self._get_active_or_404(uow, product_id)

        if product.type == ProductType.MANUFACTURED:

            ingredients_ids = [
                ingredient.ingredient_id for ingredient in product.ingredients
            ]

            ingredients = uow.ingredients.get_active_by_ids(ingredients_ids)
            ingredients_map = {i.id: i for i in ingredients}

            stocks_values = []

            for rel in product.ingredients:
                ing = ingredients_map.get(rel.ingredient_id)
                if ing is None or ing.stock is None or rel.quantity_ingredient == 0:
                    return 0
                stocks_values.append(ing.stock // rel.quantity_ingredient)

            return min(stocks_values) if stocks_values else 0

        return product.stock  # type: ignore

    def calculate_manufactured_stock(self, data: CalculateStockRequest) -> int:
        if not data.ingredients:
            return 0

        with ProductUnitOfWork(self._session) as uow:
            ids = [i.ingredient_id for i in data.ingredients]
            ingredients = uow.ingredients.get_active_by_ids(ids)
            ingredients_map = {i.id: i for i in ingredients}

            stocks = []
            for item in data.ingredients:
                ing = ingredients_map.get(item.ingredient_id)
                if ing is None or ing.stock is None or item.quantity_ingredient == 0:
                    return 0
                stocks.append(int(ing.stock // item.quantity_ingredient))

            return min(stocks) if stocks else 0

    def create(self, data: ProductCreate) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)
            primary_category = self._get_category_active_or_404(uow, data.category_id)

            # si es manufacturado forzamos none en stock
            if data.type == ProductType.MANUFACTURED:
                data.stock = None

            if data.sales_unit is not None:
                self._assert_sales_unit_exists(data.sales_unit)

            product = Product.model_validate(data.model_dump(exclude={"ingredients"}))

            uow.products.add(product)

            categories = list(uow.categories.get_all_no_paged())
            category_map = self._build_category_map(categories)
            chain_ids = self._build_parent_chain(primary_category, category_map)

            uow.product_category_link.create_chain(
                product.id, chain_ids, data.category_id  # type: ignore
            )

            if data.ingredients:
                self._add_ingredients(uow, product, data.ingredients)

            result = ProductPublic.model_validate(product)
        return result

    def list_all_public(self, filters: ProductFilters) -> ProductList:
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all_active(filters, True)
            total = uow.products.count_query(filters)

            manufactured_ids = [
                p.id for p in products if p.type == ProductType.MANUFACTURED
            ]
            if manufactured_ids:
                stocks = uow.products.get_manufactured_stocks_batch(manufactured_ids)  # type: ignore
                for p in products:
                    if p.id in stocks:
                        p.stock = stocks[p.id]

            data = [ProductPublic.model_validate(p) for p in products]
            result = ProductList(data=data, total=total)

        return result

    def list_all_admin(self, filters: ProductFilters):
        with ProductUnitOfWork(self._session) as uow:
            products = uow.products.get_all_active(filters, False)
            total = uow.products.count_query(filters)

            manufactured_ids = [
                p.id for p in products if p.type == ProductType.MANUFACTURED
            ]
            if manufactured_ids:
                stocks = uow.products.get_manufactured_stocks_batch(manufactured_ids)  # type: ignore
                for p in products:
                    if p.id in stocks:
                        p.stock = stocks[p.id]

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

                    categories = list(uow.categories.get_all_no_paged())
                    category_map = self._build_category_map(categories)
                    chain_ids = self._build_parent_chain(new_category, category_map)

                    uow.product_category_link.create_chain(
                        product_id, chain_ids, new_category.id  # type: ignore
                    )

            exclude_fields = {"category_id"}

            if data.sales_unit is not None:
                self._assert_sales_unit_exists(data.sales_unit)

            # manejar cambio de tipo (antes de validar stock, así usa el tipo nuevo)
            if data.type is not None and data.type != product.type:
                self._update_type(product, data.type, uow)
                exclude_fields.add("type")

            # no permitir cambiar stock a productos manufacturados
            if data.stock is not None and product.type == ProductType.MANUFACTURED:
                exclude_fields.add("stock")

            patch = data.model_dump(exclude_unset=True, exclude=exclude_fields)
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
                raise BusinessRuleError(
                    message="No se puede restaurar un producto que no está eliminado",
                )
            uow.products.restore(product)
            result = ProductAdmin.model_validate(product)
        return result

    def get_active_by_id_with_details(self, product_id: int) -> ProductDetail:
        with ProductUnitOfWork(self._session) as uow:
            product, categories, primary, ingredients = self._get_details_or_404(
                uow, product_id, active_only=True
            )

            if product.type == ProductType.MANUFACTURED:
                product.stock = self._get_product_stock(uow, product.id)  # type: ignore

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

            if product.type == ProductType.MANUFACTURED:
                product.stock = self._get_product_stock(uow, product.id)  # type: ignore

            return ProductAdminDetail(
                **ProductAdmin.model_validate(product).model_dump(),
                primary_category=primary,
                categories=categories,
                ingredients=ingredients,
            )

    def update_stock(self, product_id: int, data: UpdateStock) -> ProductPublic:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)
            if product.type == ProductType.MANUFACTURED:
                raise BusinessRuleError(
                    "No se puede actualizar el stock de un producto manufacturado",
                )
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

    def _update_type(
        self, product: Product, new_type: ProductType, uow: ProductUnitOfWork
    ) -> None:
        if new_type == product.type:
            return
        if new_type == ProductType.MANUFACTURED:
            product.stock = None
        else:
            product.stock = 0
            uow.product_ingredient.remove_by_product(product.id)  # type: ignore

        product.type = new_type

    def update_type(self, product_id: int, data: UpdateType) -> ProductAdmin:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_or_404(uow, product_id)
            self._update_type(product, data.type, uow)
            product.updated_at = datetime.now(timezone.utc)
            uow.products.add(product)

        return ProductAdmin.model_validate(product)

    def add_ingredients(
        self, product_id: int, ingredients: list[ProductIngredientBatchItem]
    ) -> ProductAdmin:
        with ProductUnitOfWork(self._session) as uow:
            product = self._get_active_or_404(uow, product_id)

            self._add_ingredients(uow, product, ingredients)

            return ProductAdmin.model_validate(product)
