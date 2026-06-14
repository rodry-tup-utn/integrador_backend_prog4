from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.order.models import PaymentMethod
from typing import Sequence


class PaymentMethodRepository(BaseRepository["PaymentMethod"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, PaymentMethod)

    def get_by_code(self, code: str) -> PaymentMethod | None:
        statement = select(PaymentMethod).where(PaymentMethod.code == code)
        return self.session.exec(statement).first()

    def get_available(self) -> Sequence[PaymentMethod]:
        statement = select(PaymentMethod).where(PaymentMethod.available == True)
        return self.session.exec(statement).all()
