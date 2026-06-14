from decimal import Decimal
from app.modules.order.unit_of_work import OrderUnitOfWork
from app.modules.product.models import Product, ProductType
from app.core.exceptions import ResourceNotFoundError, BusinessRuleError


class StockService:
    def get_product_map(
        self, uow: OrderUnitOfWork, product_ids: list[int]
    ) -> dict[int, Product]:
        products = uow.products.get_by_ids(product_ids)
        return {p.id: p for p in products}  # type: ignore

    def check_stock_final(self, items: list, product_map: dict[int, Product]) -> None:
        for item in items:
            product = product_map.get(item.product_id)
            if not product:
                raise ResourceNotFoundError(resource="Producto", identifier=item.product_id)
            if product.stock is not None and product.stock < item.quantity:
                raise BusinessRuleError(
                    f"Stock insuficiente para '{product.name}': "
                    f"disponible {product.stock}, solicitado {item.quantity}",
                )

    def compute_ingredient_needs(
        self, uow: OrderUnitOfWork, items: list[tuple[int, int, list[int] | None]]
    ) -> dict[int, Decimal]:
        product_ids = [product_id for product_id, _, _ in items]
        all_relations = uow.product_ingredients.get_by_products(product_ids)

        needs: dict[int, Decimal] = {}
        for pid, qty, removed in items:
            for rel in all_relations:
                if rel.product_id == pid and rel.ingredient_id not in (removed or []):
                    needs[rel.ingredient_id] = (
                        needs.get(rel.ingredient_id, Decimal("0"))
                        + rel.quantity_ingredient * qty
                    )
        return needs

    def validate_ingredient_stock(
        self, uow: OrderUnitOfWork, items: list[tuple[int, int, list[int] | None]]
    ) -> None:
        needs = self.compute_ingredient_needs(uow, items)
        ingredients = {
            i.id: i for i in uow.ingredients.get_active_by_ids(list(needs.keys()))
        }

        for ing_id, required in needs.items():
            ing = ingredients.get(ing_id)
            if not ing or (ing.stock is not None and ing.stock < required):
                name = ing.name if ing else str(ing_id)
                raise BusinessRuleError(
                    f"Stock insuficiente del ingrediente '{name}': "
                    f"necesario {required}",
                )

    def validate_and_split_items(
        self, uow: OrderUnitOfWork, items: list, product_map: dict[int, Product]
    ) -> tuple[list, list]:
        final_items, manufactured_items = [], []
        for item in items:
            product = product_map.get(item.product_id)
            if not product:
                raise ResourceNotFoundError(resource="Producto", identifier=item.product_id)
            if product.type == ProductType.MANUFACTURED:
                manufactured_items.append(item)
            else:
                final_items.append(item)

        if final_items:
            self.check_stock_final(final_items, product_map)
        if manufactured_items:
            self.validate_ingredient_stock(
                uow,
                [
                    (i.product_id, i.quantity, i.personalization)
                    for i in manufactured_items
                ],
            )

        return final_items, manufactured_items

    def validate_personalization(self, uow: OrderUnitOfWork, items: list) -> None:
        product_ids = [item.product_id for item in items]
        all_relations = uow.product_ingredients.get_by_products(product_ids)

        for item in items:
            if not item.personalization:
                continue
            product_relations = [
                r for r in all_relations if r.product_id == item.product_id
            ]
            removable_ids = {
                r.ingredient_id for r in product_relations if r.is_removable
            }
            for ing_id in item.personalization:
                if ing_id not in removable_ids:
                    raise BusinessRuleError(
                        f"El ingrediente {ing_id} no es removible "
                        f"para el producto {item.product_id}",
                    )

    def restore_stock_for_simple_products(
        self, uow: OrderUnitOfWork, items: list
    ) -> None:
        product_ids = [i.product_id for i in items]
        final_ids = uow.products.get_final_product_ids(product_ids)
        increase_items = [
            (i.product_id, i.quantity) for i in items if i.product_id in final_ids
        ]
        if increase_items:
            uow.products.increase_stock_batch(increase_items)

    def restore_ingredient_stock(self, uow: OrderUnitOfWork, items: list) -> None:
        needs = self.compute_ingredient_needs(
            uow,
            [(i.product_id, i.quantity, i.personalization) for i in items],
        )
        if needs:
            uow.ingredients.increase_stock_batch(list(needs.items()))
