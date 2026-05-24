from sqlmodel import SQLModel, Field
from datetime import datetime
from decimal import Decimal
from app.modules.order_item.schemas import OrderItemCreate, OrderItemPublic


class OrderCreate(SQLModel):
    address_id: int = Field(ge=1)
    payment_method_code: str = Field(max_length=20)
    notes: str | None = Field(default=None, max_length=255)
    items: list[OrderItemCreate]
    discount: Decimal | None = Field(default=Decimal("0.00"), ge=0)
    shipping_cost: Decimal | None = Field(default=Decimal("0.00"), ge=0)


class OrderUserPublic(SQLModel):
    id: int
    name: str
    lastname: str


class OrderAddressPublic(SQLModel):
    id: int
    alias: str
    line_one: str
    city: str
    province: str


class StateOrderPublic(SQLModel):
    code: str
    description: str


class OrderHistorialPublic(SQLModel):
    id: int
    state_from_code: str | None
    state_to_code: str
    reason: str | None
    created_at: datetime


class OrderPublic(SQLModel):
    id: int
    user_id: int
    address_id: int
    state_code: str
    payment_method_code: str
    subtotal: Decimal
    discount: Decimal
    shipping_cost: Decimal
    notes: str | None
    created_at: datetime


class OrderDetailPublic(OrderPublic):
    user: OrderUserPublic
    address: OrderAddressPublic
    state: StateOrderPublic
    items: list[OrderItemPublic]
    historials: list[OrderHistorialPublic]


class OrderList(SQLModel):
    data: list[OrderPublic]
    total: int


class OrderStateChange(SQLModel):
    state_code: str = Field(max_length=20)
    reason: str | None = Field(default=None, max_length=255)


class OrderCancelByStaff(SQLModel):
    reason: str = Field(max_length=255)
