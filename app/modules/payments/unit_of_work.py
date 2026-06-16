from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.payments.repository import PaymentRepository
from app.modules.order.repositories.order_repository import OrderRepository


class PaymentUnitOfWork(UnitOfWork["PaymentUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.paymentsRepo = PaymentRepository(session)
        self.ordersRepo = OrderRepository(session)
