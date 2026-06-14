from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.order.models import StateOrder
from typing import Sequence


class StateOrderRepository(BaseRepository["StateOrder"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, StateOrder)

    def get_by_code(self, code: str) -> StateOrder | None:
        statement = select(StateOrder).where(StateOrder.code == code)
        return self.session.exec(statement).first()

    def get_all_ordered(self) -> Sequence[StateOrder]:
        statement = select(StateOrder).order_by(col(StateOrder.order))
        return self.session.exec(statement).all()
