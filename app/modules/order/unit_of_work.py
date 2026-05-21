from app.core.unit_of_work import UnitOfWork
from sqlmodel import Session
from app.modules.order.repositories.order_repository import OrderRepository
from app.modules.order.repositories.order_historial_repository import OrderHistorialRepository
from app.modules.order.repositories.state_order_repository import StateOrderRepository
from app.modules.order.repositories.payload_method_repository import PayloadMethodRepository
from app.modules.order_item.repository import OrderItemRepository


class OrderUnitOfWork(UnitOfWork["OrderUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.orders = OrderRepository(session)
        self.historials = OrderHistorialRepository(session)
        self.order_items = OrderItemRepository(session)
        self.states = StateOrderRepository(session)
        self.payload_methods = PayloadMethodRepository(session)
