from sqlmodel import SQLModel, Field
from decimal import Decimal


class OrderItemCreate(SQLModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1)
    personalization: list[int] | None = Field(default=None)


class OrderItemPublic(SQLModel):
    product_id: int
    quantity: int
    name_snap: str
    price_snap: Decimal
    subtotal_snap: Decimal
    personalization: list[int] | None
