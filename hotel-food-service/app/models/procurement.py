import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow


class PurchaseOrderStatus(enum.StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrder(TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.DRAFT, nullable=False
    )
    expected_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    total_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    supplier = relationship("Supplier")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.id",
    )
    receipts: Mapped[list["GoodsReceipt"]] = relationship(back_populates="purchase_order")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id"), index=True, nullable=False
    )
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    ingredient = relationship("Ingredient")

    @property
    def line_total_minor(self) -> int:
        from app.core.money import multiply

        return multiply(self.unit_price_minor, self.quantity)

    @property
    def outstanding_quantity(self) -> float:
        return max(self.quantity - self.received_quantity, 0.0)


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id"), index=True, nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="receipts")
    lines: Mapped[list["GoodsReceiptLine"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("goods_receipts.id"), nullable=False)
    purchase_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_lines.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")
    purchase_order_line = relationship("PurchaseOrderLine")
