from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, BigInteger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.order.models import Order


class Payment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")

    mp_payment_id: int | None = Field(default=None, sa_type=BigInteger)
    mp_status: str | None = Field(max_length=30)
    mp_status_detail: str | None = Field(default=None, max_length=100)
    external_reference: str | None = Field(max_length=100)
    idempotency_key: str = Field(max_length=100, unique=True)
    transaction_amount: Decimal = Field(ge=0)
    payment_method_id: str | None = Field(default=None, max_length=50)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    order: "Order" = Relationship(back_populates="payments")
