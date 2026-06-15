from sqlmodel import Session, select
from typing import Sequence
from datetime import datetime, timezone

from app.core.repository import BaseRepository
from app.modules.payments.models import Payment


class PaymentRepository(BaseRepository[Payment]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Payment)

    # Obtiene los pagos asociados a un pedido
    def get_payments_by_order_id(self, order_id: int) -> Sequence[Payment]:
        statement = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
        )
        return self.session.exec(statement).all()

    # Obtiene un pago en específico por el id de MercadoPago
    def get_by_mp_payment_id(self, mp_payment_id: int) -> Payment | None:
        statement = select(Payment).where(Payment.mp_payment_id == mp_payment_id)
        return self.session.exec(statement).first()

    # Obtiene un pago por el external_reference devuelto por MP
    def get_by_external_reference(self, external_reference: str) -> Payment | None:
        statement = select(Payment).where(
            Payment.external_reference == external_reference
        )
        return self.session.exec(statement).first()

    # Revisa y devuelve el payment en estado pendiente más reciente
    def get_pending_by_order_id(self, order_id: int) -> Payment | None:
        statement = (
            select(Payment)
            .where(Payment.order_id == order_id, Payment.mp_status == "pending")
            .order_by(Payment.created_at.desc())  # type: ignore
        )

        return self.session.exec(statement).first()
