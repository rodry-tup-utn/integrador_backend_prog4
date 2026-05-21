from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.order.models import OrderHistorial
from typing import Sequence


class OrderHistorialRepository(BaseRepository["OrderHistorial"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, OrderHistorial)

    def create_entry(
        self,
        order_id: int,
        state_from_code: str,
        state_to_code: str,
        reason: str | None = None,
    ) -> OrderHistorial:
        entry = OrderHistorial(
            order_id=order_id,
            state_from_code=state_from_code,
            state_to_code=state_to_code,
            reason=reason,
        )
        self.session.add(entry)
        self.session.flush()
        self.session.refresh(entry)
        return entry

    def get_by_order(self, order_id: int) -> Sequence[OrderHistorial]:
        statement = (
            select(OrderHistorial)
            .where(OrderHistorial.order_id == order_id)
            .order_by(col(OrderHistorial.created_at).desc())
        )
        return self.session.exec(statement).all()
