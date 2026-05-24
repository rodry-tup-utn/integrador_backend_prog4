from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.order_item.models import OrderItem
from typing import Sequence
from sqlalchemy import func


class OrderItemRepository(BaseRepository["OrderItem"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, OrderItem)

    def bulk_create(self, order_id: int, items_data: list[dict]) -> list[OrderItem]:
        items = []
        for data in items_data:
            item = OrderItem(
                order_id=order_id,
                product_id=data["product_id"],
                quantity=data["quantity"],
                name_snap=data["name_snap"],
                price_snap=data["price_snap"],
                subtotal_snap=data["quantity"] * data["price_snap"],
                personalization=data.get("personalization"),
            )
            items.append(item)

        self.session.add_all(items)
        self.session.flush()
        for item in items:
            self.session.refresh(item)
        return items

    def get_by_order(self, order_id: int) -> Sequence[OrderItem]:
        statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(col(OrderItem.product_id))
        )
        return self.session.exec(statement).all()

    def delete_by_order(self, order_id: int) -> None:
        statement = select(OrderItem).where(OrderItem.order_id == order_id)
        items = self.session.exec(statement).all()
        for item in items:
            self.session.delete(item)
        self.session.flush()

    def get_by_product(self, product_id: int, offset: int = 0, limit: int = 20) -> Sequence[OrderItem]:
        statement = (
            select(OrderItem)
            .where(OrderItem.product_id == product_id)
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def count_by_product(self, product_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(OrderItem)
            .where(OrderItem.product_id == product_id)
        )
        return self.session.exec(statement).one()
