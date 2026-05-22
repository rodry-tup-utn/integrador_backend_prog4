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
    OrderHistorialPublic,
    OrderUserPublic,
    OrderAddressPublic,
)
from app.modules.order_item.schemas import OrderItemPublic
from app.modules.product.models import Product
from app.modules.user.models import Address

PENDING_STATE = "PENDING"
CANCELLED_STATE = "CANCELLED"
IN_PREP = "IN_PREP"

NOT_UPDATABLE_BY_CLIENT = {"PENDING", "CONFIRMED", "IN_PREP"}
NOT_UPDATABLE_BY_STAFF = {"PENDING", "CONFIRMED"}


class OrderService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_product_map(
        self, uow: OrderUnitOfWork, product_ids: list[int]
    ) -> dict[int, Product]:
        products = uow.products.get_by_ids(product_ids)
        return {p.id: p for p in products}  # type: ignore

    def _check_stock(self, items: list, product_map: dict[int, Product]) -> None:
        for item in items:
            product = product_map.get(item.product_id)
            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Producto con id {item.product_id} no encontrado",
                )
            if product.stock < item.quantity:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Stock insuficiente para '{product.name}': "
                    f"disponible {product.stock}, solicitado {item.quantity}",
                )

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

    def create(self, data: OrderCreate, user_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            product_ids = [item.product_id for item in data.items]
            product_map = self._get_product_map(uow, product_ids)

            # validar stock
            self._check_stock(data.items, product_map)
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

            decrease_items = [(item.product_id, item.quantity) for item in data.items]
            uow.products.decrease_stock_batch(decrease_items)

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def get_by_id(self, order_id: int, user_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = uow.orders.get_by_id_with_details(order_id)
            if not order:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
            if order.user_id != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para ver este pedido",
                )
            return self._order_to_detail(order)

    def get_by_id_admin(self, order_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = uow.orders.get_by_id_with_details(order_id)
            if not order:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
            return self._order_to_detail(order)

    def list_by_user(self, user_id: int, offset: int = 0, limit: int = 20) -> OrderList:
        with OrderUnitOfWork(self._session) as uow:
            orders = uow.orders.get_by_user_id(user_id, offset, limit)
            total = uow.orders.count_by_user(user_id)
            data = [OrderPublic.model_validate(o) for o in orders]
            return OrderList(data=data, total=total)

    def list_all(self, offset: int = 0, limit: int = 20) -> OrderList:
        with OrderUnitOfWork(self._session) as uow:
            orders = uow.orders.get_all(offset, limit)
            total = uow.orders.count()
            data = [OrderPublic.model_validate(o) for o in orders]
            return OrderList(data=data, total=total)

    def cancel(
        self, order_id: int, user_id: int, reason: str = "Cancelado por el usuario"
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = uow.orders.get_by_id(order_id)
            if not order:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
            if order.user_id != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para cancelar este pedido",
                )

            self._check_update_state(order.state_code, NOT_UPDATABLE_BY_CLIENT)

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
            increase_items = [(i.product_id, i.quantity) for i in items]
            uow.products.increase_stock_batch(increase_items)

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def change_state(
        self, order_id: int, new_state_code: str, reason: str | None = None
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = uow.orders.get_by_id(order_id)
            if not order:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

            new_state = self._check_state_order(uow, new_state_code)

            self._check_update_state(order.state_code, NOT_UPDATABLE_BY_STAFF)

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
                uow.products.increase_stock_batch(
                    [(i.product_id, i.quantity) for i in items]
                )

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore

    def cancel_by_staff(self, order_id: int, reason: str) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = uow.orders.get_by_id(order_id)
            if not order:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

            self._check_update_state(order.state_code, NOT_UPDATABLE_BY_STAFF)

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
            increase_items = [(i.product_id, i.quantity) for i in items]
            uow.products.increase_stock_batch(increase_items)

            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore
            return self._order_to_detail(order_detail)  # type: ignore
