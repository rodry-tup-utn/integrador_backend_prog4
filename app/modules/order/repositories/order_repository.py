from datetime import datetime, timezone
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.user.models import User
from app.modules.order.models import Order, StateOrder
from sqlalchemy.orm import selectinload
from typing import Sequence
from sqlalchemy import func, or_, cast, String


class OrderRepository(BaseRepository["Order"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Order)

    # metodo para agregar detalles completos de la orden
    def _base_detail_options(self):
        return [
            selectinload(Order.user),
            selectinload(Order.address),
            selectinload(Order.state),
            selectinload(Order.payload_method),
            selectinload(Order.order_items),
            selectinload(Order.historials),
        ]

    def get_by_id_with_details(self, id: int) -> Order | None:
        statement = (
            select(Order)
            .where(Order.id == id)
            .options(
                *self._base_detail_options()
            )  # carga todos los detalles de la orden
        )
        return self.session.exec(statement).first()

    def get_all_with_details(self, offset: int = 0, limit: int = 20) -> Sequence[Order]:
        statement = (
            select(Order)
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def get_by_user_id(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Order]:
        statement = (
            select(Order)
            .where(Order.user_id == user_id)
            .offset(offset)
            .limit(limit)
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def get_by_user_id_with_details(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Order]:
        statement = (
            select(Order)
            .where(Order.user_id == user_id)
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def get_non_terminal_by_user(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Order]:
        statement = (
            select(Order)
            .join(StateOrder, Order.state_code == StateOrder.code)
            .where(
                Order.user_id == user_id, StateOrder.is_terminal == False  # noqa: E712
            )  # noqa: E712
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def get_by_state(
        self, state_code: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Order]:
        statement = (
            select(Order)
            .where(Order.state_code == state_code)
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def count_by_state(self, state_code: str) -> int:
        statement = (
            select(func.count())
            .select_from(Order)
            .where(Order.state_code == state_code)
        )
        return self.session.exec(statement).one()

    def count_by_user(self, user_id: int) -> int:
        statement = (
            select(func.count()).select_from(Order).where(Order.user_id == user_id)
        )
        return self.session.exec(statement).one()

    def get_by_date_range(
        self, start: datetime, end: datetime, offset: int = 0, limit: int = 20
    ) -> Sequence[Order]:
        statement = (
            select(Order)
            .where(Order.created_at >= start, Order.created_at <= end)
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def count_by_date_range(self, start: datetime, end: datetime) -> int:
        statement = (
            select(func.count())
            .select_from(Order)
            .where(Order.created_at >= start, Order.created_at <= end)
        )
        return self.session.exec(statement).one()

    def update(self, order: Order, update_data: dict) -> Order:
        for field, value in update_data.items():
            setattr(order, field, value)
        order.updated_at = datetime.now(timezone.utc)
        self.session.add(order)
        self.session.flush()
        self.session.refresh(order)
        return order

    def update_state(self, order: Order, new_state_code: str) -> Order:
        order.state_code = new_state_code
        order.updated_at = datetime.now(timezone.utc)
        self.session.add(order)
        self.session.flush()
        self.session.refresh(order)
        return order

    def soft_delete(self, order: Order) -> None:
        order.deleted_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        self.session.add(order)
        self.session.flush()

    def restore(self, order: Order) -> Order:
        order.deleted_at = None
        order.updated_at = datetime.now(timezone.utc)
        self.session.add(order)
        self.session.flush()
        self.session.refresh(order)
        return order

    def search(self, query: str, offset: int = 0, limit: int = 20) -> Sequence[Order]:
        statement = (
            select(Order)
            .join(User, Order.user_id == User.id)
            .where(
                or_(
                    cast(Order.id, String).ilike(f"%{query}%"),  # type: ignore
                    col(User.name).ilike(f"%{query}%"),
                    col(User.lastname).ilike(f"%{query}%"),
                )
            )
            .offset(offset)
            .limit(limit)
            .options(*self._base_detail_options())
            .order_by(col(Order.created_at).desc())
        )
        return self.session.exec(statement).all()

    def count_search_results(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(Order)
            .join(User, Order.user_id == User.id)
            .where(
                or_(
                    cast(Order.id, String).ilike(f"%{query}%"),  # type: ignore
                    col(User.name).ilike(f"%{query}%"),
                    col(User.lastname).ilike(f"%{query}%"),
                )
            )
        )
        return self.session.exec(statement).one()
