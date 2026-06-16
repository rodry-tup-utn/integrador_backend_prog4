from sqlmodel import SQLModel, Field
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime


class PaymentCreate(SQLModel):
    order_id: int = Field(ge=0)
    mp_payment_id: int | None = Field(default=None)
    mp_status: str = Field(max_length=30)
    mp_status_detail: str | None = Field(default=None, max_length=100)
    external_reference: str = Field(max_length=100)
    idempotency_key: str = Field(max_length=100)
    transaction_amount: Decimal = Field(ge=0)
    payment_method_id: str | None = Field(default=None, max_length=50)


class PaymentRead(PaymentCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class PaymentUpdate(SQLModel):
    mp_payment_id: int | None = Field(default=None)
    mp_status: str | None = Field(max_length=30)
    mp_status_detail: str | None = Field(default=None, max_length=100)
    payment_method_id: str | None = Field(default=None, max_length=50)
    updated_at: datetime | None = Field(default=lambda: datetime.now(timezone.utc))


class PaymentPublic(SQLModel):
    id: int
    order_id: int
    mp_payment_id: int | None
    mp_status: str | None
    mp_status_detail: str | None
    transaction_amount: Decimal
    payment_metho_id: str | None
    created_at: datetime
    updated_at: datetime | None


class CheckoutPreferenceResponse(SQLModel):
    payment_id: int
    preference_id: str
    init_point: str
    sandbox_init_point: str


class MPWebhookNotification(SQLModel):
    type: str | None = Field(default=None)
    action: str | None = Field(default=None)
    data: dict | None = Field(default=None)
