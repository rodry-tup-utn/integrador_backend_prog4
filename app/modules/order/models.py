from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from app.modules.user.models import User, Address
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.order_item.models import OrderItem


class PayloadMethod(SQLModel, table=True):
    __tablename__ = "payload_method"  # type: ignore

    code: str = Field(max_length=20, primary_key=True)
    description: str = Field(min_length=3, max_length=255)
    available: bool = Field(default=True)

    orders: list["Order"] = Relationship(back_populates="payload_method")


class StateOrder(SQLModel, table=True):
    __tablename__ = "state_order"  # type: ignore
    code: str = Field(max_length=20, primary_key=True)
    description: str = Field(max_length=80)
    order: int
    is_terminal: bool

    orders: list["Order"] = Relationship(back_populates="state")
    historials_from: list["OrderHistorial"] = Relationship(back_populates="state_from")
    historials_to: list["OrderHistorial"] = Relationship(back_populates="state_to")


class OrderHistorial(SQLModel, table=True):
    __tablename__ = "order_historial"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    state_from_code: str = Field(foreign_key="state_order.code")
    state_to_code: str = Field(foreign_key="state_order.code")
    reason: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    state_from: StateOrder = Relationship(
        back_populates="historials_from",
        sa_relationship_kwargs={"foreign_keys": "[OrderHistorial.state_from_code]"},
    )
    state_to: StateOrder = Relationship(
        back_populates="historials_to",
        sa_relationship_kwargs={"foreign_keys": "[OrderHistorial.state_to_code]"},
    )
    order: "Order" = Relationship(back_populates="historials")


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    address_id: int = Field(foreign_key="address.id")
    state_code: str = Field(foreign_key="state_order.code")
    payload_method_code: str = Field(foreign_key="payload_method.code")

    subtotal: Decimal = Field(ge=0)
    discount: Decimal = Field(ge=0)
    shipping_cost: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, min_length=3, max_length=255)

    payload_method: PayloadMethod = Relationship(back_populates="orders")
    state: StateOrder = Relationship(back_populates="orders")
    user: User = Relationship(back_populates="orders")
    address: Address = Relationship(back_populates="orders")
    historials: list["OrderHistorial"] = Relationship(back_populates="order")
    order_items: list["OrderItem"] = Relationship(back_populates="order")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
