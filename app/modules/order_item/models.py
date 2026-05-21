from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.order.models import Order
    from app.modules.product.models import Product


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_item"  # type: ignore

    order_id: int = Field(foreign_key="order.id", primary_key=True)
    product_id: int = Field(foreign_key="product.id", primary_key=True)

    quantity: int = Field(ge=1)

    name_snap: str = Field(min_length=3, max_length=200)
    price_snap: Decimal = Field(ge=0)
    subtotal_snap: Decimal = Field(ge=0)
    personalization: list[int] | None = Field(
        default=None,
        sa_column=Column(ARRAY(Integer)),
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    order: "Order" = Relationship(back_populates="order_items")
    product: "Product" = Relationship(back_populates="order_items")
