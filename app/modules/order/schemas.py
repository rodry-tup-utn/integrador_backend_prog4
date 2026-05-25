from sqlmodel import SQLModel, Field
from datetime import datetime
from decimal import Decimal
from app.modules.order_item.schemas import OrderItemCreate, OrderItemPublic
from typing import Literal, Annotated
from pydantic import Field as PydanticField


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


class OrderClientFilters(SQLModel):
    state_code: (
        Literal["PENDING", "CONFIRMED", "IN_PREP", "DELIVERED", "CANCELLED"] | None
    ) = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    offset: Annotated[int, PydanticField(ge=0)] = 0
    limit: Annotated[int, PydanticField(ge=1)] = 20
    sort_by: Literal["created_at", "subtotal", "id"] = "created_at"
    order: Literal["asc", "desc"] = "desc"


class OrderFilters(OrderClientFilters):
    user_id: Annotated[int | None, PydanticField(ge=1)] = None
    user_email: Annotated[str | None, PydanticField(min_length=3, max_length=20)] = None
    user_lastname: Annotated[str | None, PydanticField(min_length=2, max_length=80)] = (
        None
    )
    user_name: Annotated[str | None, PydanticField(min_length=2, max_length=80)] = None
