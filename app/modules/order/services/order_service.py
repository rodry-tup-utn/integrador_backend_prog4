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
from app.modules.product.models import Product
from app.modules.user.models import Address
from datetime import datetime, timezone
from app.modules.order.services.stock_service import StockService
from app.modules.order.services.state_service import OrderStateService
import logging
from app.modules.websocket.manager import manager

logger = logging.getLogger("app.modules.orders.services.order_service")

STATES = {
    OrderStateService.PENDING,
    OrderStateService.CONFIRMED,
    OrderStateService.IN_PREP,
    OrderStateService.DELIVERED,
    OrderStateService.CANCELLED,
}

ROLES_BY_TRANSITION = {
    "PENDING": ["ORDERS", "ADMIN"],
    "CONFIRMED": ["ORDERS", "ADMIN"],
    "IN_PREP": ["ORDERS", "ADMIN"],
    "DELIVERED": ["ORDERS", "ADMIN"],
    "CANCELLED": ["ORDERS", "ADMIN"],
}

WS_EVENT_ORDER_CREATED = "order_created"
WS_EVENT_ORDER_UPDATED = "order_updated"


class OrderService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.stock = StockService()
        self.state = OrderStateService()

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

    def _update_order(self, uow: OrderUnitOfWork, order: Order):
        now = datetime.now(timezone.utc)
        order.updated_at = now
        uow.orders.add(order)
        return order

    def _get_or_404(self, uow: OrderUnitOfWork, order_id: int):
        order = uow.orders.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Orden id {order_id} no encontrada"
            )
        return order

    async def _emit_ws_events(
        self, order_id: int, new_state: str, event: str
    ) -> None:

        if new_state not in STATES:
            return

        data = {"order_id": order_id, "state": new_state}

        await manager.broadcast_to_order(order_id, event, data)

        roles_a_notificar = ROLES_BY_TRANSITION.get(new_state, [])
        if roles_a_notificar:
            await manager.broadcast_to_roles(roles_a_notificar, event, data)

        logger.info(
            f"WS emitido: {event} | pedido={order_id} | "
            f"roles={roles_a_notificar} | rooms_activas={manager.get_rooms_info()}"
        )

    async def create(self, data: OrderCreate, user_id: int) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            product_ids = [item.product_id for item in data.items]
            product_map = self.stock.get_product_map(uow, product_ids)

            self.stock.validate_and_split_items(uow, data.items, product_map)
            self.stock.validate_personalization(uow, data.items)

            payload = self._check_payment_method(uow, data.payment_method_code)
            state = self.state.check_state_order(uow, self.state.PENDING)
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
            result = self._order_to_detail(order_detail)  # type: ignore
            await self._emit_ws_events(order.id, state.code, WS_EVENT_ORDER_CREATED)  # type: ignore

            return result

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

    async def cancel(
        self, order_id: int, user_id: int, reason: str = "Cancelado por el usuario"
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)
            if order.user_id != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para cancelar este pedido",
                )

            self.state.check_update_state(order.state_code, self.state.TERMINAL_CLIENT)

            state = self.state.check_state_order(uow, self.state.CANCELLED)
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

            if old_state != self.state.PENDING:
                self.stock.restore_stock_for_simple_products(uow, list(items))
                if old_state == self.state.CONFIRMED:
                    self.stock.restore_ingredient_stock(uow, list(items))

            order = self._update_order(uow, order)
            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore

            result = self._order_to_detail(order_detail)  # type: ignore
            await self._emit_ws_events(order.id, state.code, WS_EVENT_ORDER_UPDATED)  # type: ignore

            return result

    async def change_state(
        self, order_id: int, new_state_code: str, reason: str | None = None
    ) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            old_state = self.state.check_state_order(uow, order.state_code)
            new_state = self.state.check_state_order(uow, new_state_code)

            self.state.check_update_state(order.state_code, self.state.TERMINAL_STAFF)

            if new_state.order - old_state.order != 1:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No puedes saltar mas de un estado",
                )

            if new_state.code == self.state.CONFIRMED:
                product_map = self.stock.get_product_map(
                    uow, [i.product_id for i in order.order_items]
                )

                final_items, manufactured_items = self.stock.validate_and_split_items(
                    uow, order.order_items, product_map
                )

                if final_items:
                    uow.products.decrease_stock_batch(
                        [(i.product_id, i.quantity) for i in final_items]
                    )
                if manufactured_items:
                    needs = self.stock.compute_ingredient_needs(
                        uow,
                        [
                            (i.product_id, i.quantity, i.personalization)
                            for i in manufactured_items
                        ],
                    )
                    uow.ingredients.decrease_stock_batch(list(needs.items()))

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

            order = self._update_order(uow, order)
            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore

            result = self._order_to_detail(order_detail)  # type: ignore

            await self._emit_ws_events(order.id, new_state.code, WS_EVENT_ORDER_UPDATED)  # type: ignore

            return result

    async def cancel_by_staff(self, order_id: int, reason: str) -> OrderDetailPublic:
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            self.state.check_update_state(order.state_code, self.state.TERMINAL_STAFF)

            state = self.state.check_state_order(uow, self.state.CANCELLED)
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
            self.stock.restore_stock_for_simple_products(uow, list(items))
            if old_state == self.state.CONFIRMED:
                self.stock.restore_ingredient_stock(uow, list(items))

            order = self._update_order(uow, order)
            order_detail = uow.orders.get_by_id_with_details(order.id)  # type: ignore

            result = self._order_to_detail(order_detail)  # type: ignore
            await self._emit_ws_events(order.id, state.code, WS_EVENT_ORDER_UPDATED)  # type: ignore

            return result

    def soft_delete(self, order_id: int):
        with OrderUnitOfWork(self._session) as uow:
            order = self._get_or_404(uow, order_id)

            if order.deleted_at is not None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "La orden ya se encuentra borrada",
                )

            now = datetime.now(timezone.utc)
            order.deleted_at = now
            uow.orders.add(order)
