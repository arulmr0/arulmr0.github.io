from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus, OrderType, PaymentMethod


class BillLine(BaseModel):
    description: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class BillPayment(BaseModel):
    method: PaymentMethod
    amount_minor: int
    paid_at: datetime


class BillRead(BaseModel):
    business_name: str
    business_address: str | None
    tax_id: str | None
    currency: str
    bill_number: str
    order_type: OrderType
    location: str | None
    status: OrderStatus
    issued_at: datetime
    guest_name: str | None
    lines: list[BillLine]
    subtotal_minor: int
    tax_rate_percent: float
    tax_minor: int
    total_minor: int
    payments: list[BillPayment]
    paid_minor: int
    balance_due_minor: int
    footer: str | None
