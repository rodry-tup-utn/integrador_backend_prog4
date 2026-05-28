from fastapi import HTTPException, status
from sqlmodel import Session
from decimal import Decimal
from app.modules.order.unit_of_work import OrderUnitOfWork
from app.modules.order.models import Order
from app.modules.order.schemas import (
    OrderCreate,
    OrderPublic,
    OrderDetailPublic,
    OrderList,
    OrderFilters,
    OrderClientFilters,
    OrderHistorialPublic,
    OrderUserPublic,
    OrderAddressPublic,
    StateOrderPublic,
    OrderAdmin,
    OrderAdminList,
)
from app.modules.order_item.schemas import OrderItemPublic
from app.modules.product.models import Product, ProductType
from app.modules.user.models import Address
from datetime import datetime, timezone

PENDING_STATE = "PENDING"
CANCELLED_STATE = "CANCELLED"
IN_PREP = "IN_PREP"
CONFIRMED_STATE = "CONFIRMED"
DELIVERED = "DELIVERED"

TERMINAL_CLIENT = {CANCELLED_STATE, DELIVERED, IN_PREP}
TERMINAL_STAFF = {CANCELLED_STATE, CONFIRMED_STATE}


class OrderService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_product_map(
        self, uow: OrderUnitOfWork, product_ids: list[int]
    ) -> dict[int, Product]:
        products = uow.products.get_by_ids(product_ids)
        return {p.id: p for p in products}  # type: ignore

    def _check_stock_final(self, items: list, product_map: dict[int, Product]) -> None:
        for item in items:
            product = product_map.get(item.product_id)
            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Producto con id {item.product_id} no encontrado",
                )
            if product.stock is not None and product.stock < item.quantity:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Stock insuficiente para '{product.name}': "
                    f"disponible {product.stock}, solicitado {item.quantity}",
                )

    # crea diccionario con id de ingrediente y cantidad necesaria (multiplicando cantidad de producto por cantidad de cada ingrediente)
    def _compute_ingredient_needs(
        self, uow: OrderUnitOfWork, items: list[tuple[int, int]]
    ) -> dict[int, Decimal]:
        product_ids = [product_id for product_id, _ in items]
        all_relations = uow.product_ingredients.get_by_products(product_ids)

        needs: dict[int, Decimal] = {}
        for pid, qty in items:
            for rel in all_relations:
                if rel.product_id == pid:
                    needs[rel.ingredient_id] = (
                        needs.get(rel.ingredient_id, Decimal("0"))
                        + rel.quantity_ingredient * qty
                    )
        return needs

    def _validate_ingredient_stock(
        self, uow: OrderUnitOfWork, items: list[tuple[int, int]]
    ) -> None:
        needs = self._compute_ingredient_needs(uow, items)
        ingredients = {
            i.id: i for i in uow.ingredients.get_active_by_ids(list(needs.keys()))
        }

        for ing_id, required in needs.items():
            ing = ingredients.get(ing_id)
            if not ing or (ing.stock is not None and ing.stock < required):
                name = ing.name if ing else str(ing_id)
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Stock insuficiente del ingrediente '{name}': "
                    f"necesario {required}",
                )

    def _validate_and_split_items(
        self, uow: OrderUnitOfWork, items: list, product_map: dict[int, Product]
    ) -> tuple[list, list]:
        final_items, manufactured_items = [], []
        for item in items:
            product = product_map.get(item.product_id)
            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Producto con id {item.product_id} no encontrado",
                )
            if product.type == ProductType.MANUFACTURED:
                manufactured_items.append(item)
            else:
                final_items.append(item)

        if final_items:
            self._check_stock_final(final_items, product_map)
        if manufactured_items:
            self._validate_ingredient_stock(
                uow, [(i.product_id, i.quantity) for i in manufactured_items]
            )

        return final_items, manufactured_items

    def _build_items_data(
        self, items: list, product_map: dict[int, Product]
    ) -> list[dict]:
        result = []
        for item in items:
            product = product_map[item.product_id]
            result.append(
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "name_snap": product.name,
                    "price_snap": product.base_price,
                    "personalization": item.personalization,
                }
            )
        return result

    def _calc_subtotal(self, items: list, product_map: dict[int, Product]) -> Decimal:
        total = Decimal("0.00")
        for item in items:
            product = product_map.get(item.product_id)
            if product:
                total += product.base_price * item.quantity
        return total

    def _validate_personalization(self, uow: OrderUnitOfWork, items: list) -> None:
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
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"El ingrediente {ing_id} no es removible "
                        f"para el producto {item.product_id}",
                    )

    def _check_payment_method(self, uow: OrderUnitOfWork, payload_code: str):
        payload = uow.payment_methods.get_by_code(payload_code)
        if not payload:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Método de pago no encontrado"
            )
        if not payload.available:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Método de pago no disponible",
            )
        return payload

    def _check_state_order(self, uow: OrderUnitOfWork, state_order: str):
        state = uow.states.get_by_code(state_order)
        if not state:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Estado {state_order} no configurado",
            )
        return state

    def _validate_address(
        self, uow: OrderUnitOfWork, address_id: int, user_id: int
    ) -> Address:
        address = uow.addresses.get_by_id(address_id)
        if not address or address.deleted_at:
            raise HTTPException(404, "Dirección no encontrada")
        if address.user_id != user_id:
            raise HTTPException(403, "La dirección no pertenece al usuario")
        return address

    def _order_to_detail(self, order: Order) -> OrderDetailPublic:
        return OrderDetailPublic(
            **OrderPublic.model_validate(order).model_dump(),
            user=OrderUserPublic.model_validate(order.user),
            address=OrderAddressPublic.model_validate(order.address),
            items=[OrderItemPublic.model_validate(i) for i in order.order_items],
            state=StateOrderPublic.model_validate(order.state),
            historials=[
                OrderHistorialPublic.model_validate(h) for h in order.historials
            ],
        )

    def _check_update_state(self, old_state: str, not_updatable_states: set[str]):

        if old_state in not_updatable_states:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La orden se encuentra en un estado no modificable",
            )

    def _restore_stock_for_simple_products(
        self, uow: OrderUnitOfWork, items: list
    ) -> None:
        product_ids = [i.product_id for i in items]
        final_ids = uow.products.get_final_product_ids(product_ids)
        increase_items = [
            (i.product_id, i.quantity) for i in items if i.product_id in final_ids
        ]
        if increase_items:
            uow.products.increase_stock_batch(increase_items)

    def _update_order(self, uow: OrderUnitOfWork, order: Order):

        now = datetime.now(timezone.utc)
        order.updated_at = now
        uow.orders.add(order)

        return order

    def _get_or_404(self, uow: OrderUnitOfWork, order_id: int):
        order = uow.orders.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Orden id {id} no encontrada"
            )

        return order

    def create(self, data: OrderCreate, user_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            product_ids = [item.product_id for item in data.items]
            product_map = self._get_product_map(uow, product_ids)

            final_items, manufactured_items = self._validate_and_split_items(
                uow, data.items, product_map
            )

            # validar ingredientes removibles
            self._validate_personalization(uow, data.items)
            # validar metodo de pago
            payload = self._check_payment_method(uow, data.payment_method_code)
            state = self._check_state_order(uow, PENDING_STATE)
            address = self._validate_address(uow, data.address_id, user_id)

            items_data = self._build_items_data(data.items, product_map)
            subtotal = self._calc_subtotal(data.items, product_map)

            order = Order(
                user_id=user_id,
                address_id=address.id,  # type: ignore
                payment_method_code=payload.code,
                state_code=state.code,
                subtotal=subtotal,
                discount=data.discount or Decimal("0.00"),
                shipping_cost=data.shipping_cost or Decimal("0.00"),
                notes=data.notes,
            )
            uow.orders.add(order)

            uow.order_items.bulk_create(order.id, items_data)  # type: ignore

            uow.historials.create_entry(
                order_id=order.id,  # type: ignore
                state_from_code=None,
                state_to_code=state.code,
                reason="Pedido creado",
            )

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def get_by_id(self, order_id: int, user_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)
            if order.user_id != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para ver este pedido",
                )
            return self._order_to_detail(order)

    def get_by_id_admin(self, order_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)
            return self._order_to_detail(order)

    def list_by_user(self, user_id: int, filters: OrderClientFilters) -> OrderList:
        filters_data = filters.model_dump()
        filters_data["user_id"] = user_id
        return self.list_all(OrderFilters(**filters_data))

    def list_all_admin(self, filters: OrderFilters) -> OrderAdminList:
        with OrderUnitOfWork(self._session) as uow:
            orders = uow.orders.get_all_with_filters(filters, False)
            total = uow.orders.count_with_filters(filters, False)

            data = [OrderAdmin.model_validate(o) for o in orders]

            return OrderAdminList(data=data, total=total)

    def list_all(self, filters: OrderFilters) -> OrderList:
        with OrderUnitOfWork(self._session) as uow:
            orders = uow.orders.get_all_with_filters(filters)
            total = uow.orders.count_with_filters(filters)
            data = [OrderPublic.model_validate(o) for o in orders]
            return OrderList(data=data, total=total)

    def cancel(
        self, order_id: int, user_id: int, reason: str = "Cancelado por el usuario"
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)
            if order.user_id != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para cancelar este pedido",
                )

            self._check_update_state(order.state_code, TERMINAL_CLIENT)

            state = self._check_state_order(uow, CANCELLED_STATE)
            if order.state_code == state.code:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "El pedido ya está cancelado",
                )

            old_state = order.state_code

            uow.orders.update_state(order, state.code)

            uow.historials.create_entry(
                order_id=order.id,  # type: ignore
                state_from_code=old_state,
                state_to_code=state.code,
                reason=reason,
            )

            items = uow.order_items.get_by_order(order.id)  # type: ignore

            if old_state != PENDING_STATE:
                self._restore_stock_for_simple_products(uow, list(items))

            order = self._update_order(uow, order)

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def change_state(
        self, order_id: int, new_state_code: str, reason: str | None = None
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            # logica para comprobar correlacion de estados
            old_state = self._check_state_order(uow, order.state_code)
            new_state = self._check_state_order(uow, new_state_code)

            if new_state.order - old_state.order != 1:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "No puedes saltar mas de un estado"
                )

            new_state = self._check_state_order(uow, new_state_code)

            # decrementar stock si pasa a confirmado
            if new_state.code == CONFIRMED_STATE:
                product_map = self._get_product_map(
                    uow, [i.product_id for i in order.order_items]
                )

                final_items, manufactured_items = self._validate_and_split_items(
                    uow, order.order_items, product_map
                )

                if final_items:
                    uow.products.decrease_stock_batch(
                        [(i.product_id, i.quantity) for i in final_items]
                    )
                if manufactured_items:
                    needs = self._compute_ingredient_needs(
                        uow,
                        [(i.product_id, i.quantity) for i in manufactured_items],
                    )
                    uow.ingredients.decrease_stock_batch(list(needs.items()))

            self._check_update_state(order.state_code, TERMINAL_STAFF)

            if order.state_code == new_state_code:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "El pedido ya está en ese estado",
                )

            old_state = order.state_code
            uow.orders.update_state(order, new_state.code)

            uow.historials.create_entry(
                order_id=order.id,  # type: ignore
                state_from_code=old_state,
                state_to_code=new_state.code,
                reason=reason,
            )

            if new_state_code == CANCELLED_STATE:
                items = uow.order_items.get_by_order(order.id)  # type: ignore
                self._restore_stock_for_simple_products(uow, list(items))

            order = self._update_order(uow, order)
            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def cancel_by_staff(self, order_id: int, reason: str) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            self._check_update_state(order.state_code, TERMINAL_STAFF)

            state = self._check_state_order(uow, CANCELLED_STATE)
            if order.state_code == state.code:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "El pedido ya está cancelado",
                )

            old_state = order.state_code
            uow.orders.update_state(order, state.code)

            uow.historials.create_entry(
                order_id=order.id,  # type: ignore
                state_from_code=old_state,
                state_to_code=state.code,
                reason=reason,
            )

            items = uow.order_items.get_by_order(order.id)  # type: ignore
            self._restore_stock_for_simple_products(uow, list(items))

            order = self._update_order(uow, order)
            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def soft_delete(self, order_id: int):
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            if order.deleted_at is not None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "La orden ya se encuentra borrada"
                )

            now = datetime.now(timezone.utc)
            order.deleted_at = now
            uow.orders.add(order)
