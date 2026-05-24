from app.core.unit_of_work import UnitOfWork
from sqlmodel import Session
from app.modules.order.repositories.order_repository import OrderRepository
from app.modules.order.repositories.order_historial_repository import (
    OrderHistorialRepository,
)
from app.modules.order.repositories.state_order_repository import StateOrderRepository
from app.modules.order.repositories.payload_method_repository import (
    PaymentMethodRepository,
)
from app.modules.order_item.repository import OrderItemRepository
from app.modules.product.repository import ProductRepository
from app.modules.product_ingredient.repository import ProductIngredientRepository
from app.modules.user.repositories.address_repository import AddressRepository


class OrderUnitOfWork(UnitOfWork["OrderUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.orders = OrderRepository(session)
        self.historials = OrderHistorialRepository(session)
        self.order_items = OrderItemRepository(session)
        self.states = StateOrderRepository(session)
        self.payment_methods = PaymentMethodRepository(session)
        self.products = ProductRepository(session)
        self.product_ingredients = ProductIngredientRepository(session)
        self.addresses = AddressRepository(session)
