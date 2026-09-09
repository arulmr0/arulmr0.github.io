from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.procurement import PurchaseOrderStatus
from app.schemas.common import ORMModel


class PurchaseOrderLineCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    unit_price_minor: int = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    expected_date: date | None = None
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1)


class PurchaseOrderLineRead(ORMModel):
    id: int
    ingredient_id: int
    quantity: float
    unit_price_minor: int
    received_quantity: float
    line_total_minor: int
    outstanding_quantity: float


class PurchaseOrderRead(ORMModel):
    id: int
    number: str
    supplier_id: int
    status: PurchaseOrderStatus
    expected_date: date | None
    notes: str | None
    total_minor: int
    created_at: datetime
    lines: list[PurchaseOrderLineRead]


class GoodsReceiptLineCreate(BaseModel):
    purchase_order_line_id: int
    quantity: float = Field(gt=0)


class GoodsReceiptCreate(BaseModel):
    notes: str | None = None
    lines: list[GoodsReceiptLineCreate] = Field(min_length=1)


class GoodsReceiptLineRead(ORMModel):
    id: int
    purchase_order_line_id: int
    quantity: float


class GoodsReceiptRead(ORMModel):
    id: int
    purchase_order_id: int
    received_at: datetime
    notes: str | None
    lines: list[GoodsReceiptLineRead]
