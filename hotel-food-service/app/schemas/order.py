from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, OrderType, PaymentMethod
from app.schemas.common import ORMModel


class OrderLineInput(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, le=500)
    notes: str | None = Field(default=None, max_length=255)


class OrderCreate(BaseModel):
    order_type: OrderType
    location: str | None = Field(default=None, max_length=40)
    lines: list[OrderLineInput] = Field(default_factory=list)


class OrderLineRead(ORMModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price_minor: int
    line_total_minor: int
    notes: str | None


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount_minor: int = Field(gt=0)


class PaymentRead(ORMModel):
    id: int
    method: PaymentMethod
    amount_minor: int
    paid_at: datetime


class OrderRead(ORMModel):
    id: int
    number: str
    order_type: OrderType
    location: str | None
    status: OrderStatus
    subtotal_minor: int
    tax_minor: int
    total_minor: int
    created_at: datetime
    closed_at: datetime | None
    lines: list[OrderLineRead]
    payments: list[PaymentRead]


class OrderStatusChange(BaseModel):
    status: OrderStatus
