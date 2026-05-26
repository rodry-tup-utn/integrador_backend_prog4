from datetime import datetime, timezone
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.user.models import User
from app.modules.order.models import Order
from app.modules.order.schemas import OrderFilters
from sqlalchemy.orm import selectinload
from typing import Sequence
from sqlalchemy import func

SORT_FIELDS = {
    "created_at": Order.created_at,
    "subtotal": Order.subtotal,
    "id": Order.id,
}


class OrderRepository(BaseRepository["Order"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Order)

    # metodo para agregar detalles completos de la orden
    def _base_detail_options(self):
        return [
            selectinload(Order.user),
            selectinload(Order.address),
            selectinload(Order.state),
            selectinload(Order.payment_method),
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

    def get_all_with_filters(
        self, filters: OrderFilters, only_actives: bool = True
    ) -> Sequence[Order]:
        statement = select(Order).offset(filters.offset).limit(filters.limit)

        if only_actives:
            statement = statement.where(col(Order.deleted_at).is_(None))
        else:
            statement = statement.options(selectinload(Order.user))

        # join en caso de mandar email o lastname
        if filters.user_email or filters.user_lastname or filters.user_name:
            statement = statement.join(User, Order.user_id == User.id)

        if filters.user_email:
            statement = statement.where(
                col(User.email).ilike(f"%{filters.user_email}%")
            )

        if filters.user_lastname:
            statement = statement.where(
                col(User.lastname).ilike(f"%{filters.user_lastname}%")
            )

        if filters.user_name:
            statement = statement.where(col(User.name).ilike(f"%{filters.user_name}%"))

        if filters.user_id is not None:
            statement = statement.where(Order.user_id == filters.user_id)

        if filters.state_code:
            statement = statement.where(Order.state_code == filters.state_code)

        if filters.date_from:
            statement = statement.where(Order.created_at >= filters.date_from)

        if filters.date_to:
            statement = statement.where(Order.created_at <= filters.date_to)

        sort_column = SORT_FIELDS.get(filters.sort_by)
        if filters.order == "asc":
            statement = statement.order_by(col(sort_column).asc())
        else:
            statement = statement.order_by(col(sort_column).desc())

        return self.session.exec(statement).all()

    def count_with_filters(
        self, filters: OrderFilters, only_actives: bool = True
    ) -> int:
        statement = select(func.count()).select_from(Order)

        if only_actives:
            statement = statement.where(col(Order.deleted_at).is_(None))

        if filters.user_email or filters.user_lastname or filters.user_name:
            statement = statement.join(User, Order.user_id == User.id)

        if filters.user_email:
            statement = statement.where(
                col(User.email).ilike(f"%{filters.user_email}%")
            )

        if filters.user_lastname:
            statement = statement.where(
                col(User.lastname).ilike(f"%{filters.user_lastname}%")
            )
        if filters.user_name:
            statement = statement.where(col(User.name).ilike(f"%{filters.user_name}%"))

        if filters.user_id is not None:
            statement = statement.where(Order.user_id == filters.user_id)

        if filters.state_code:
            statement = statement.where(Order.state_code == filters.state_code)

        if filters.date_from:
            statement = statement.where(Order.created_at >= filters.date_from)

        if filters.date_to:
            statement = statement.where(Order.created_at <= filters.date_to)

        return self.session.exec(statement).one()

    def update_state(self, order: Order, new_state_code: str) -> Order:
        order.state_code = new_state_code
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
