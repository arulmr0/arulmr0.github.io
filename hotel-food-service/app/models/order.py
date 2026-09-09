import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow


class OrderType(enum.StrEnum):
    DINE_IN = "dine_in"
    ROOM_SERVICE = "room_service"
    TAKEAWAY = "takeaway"


class OrderStatus(enum.StrEnum):
    OPEN = "open"
    IN_KITCHEN = "in_kitchen"
    SERVED = "served"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(enum.StrEnum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    ROOM_CHARGE = "room_charge"


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    location: Mapped[str | None] = mapped_column(String(40))  # table no. or room no.
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.OPEN, nullable=False, index=True
    )
    subtotal_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderLine.id"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)  # price at time of sale
    notes: Mapped[str | None] = mapped_column(String(255))

    order: Mapped[Order] = relationship(back_populates="lines")
    menu_item = relationship("MenuItem")

    @property
    def line_total_minor(self) -> int:
        return self.unit_price_minor * self.quantity


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    order: Mapped[Order] = relationship(back_populates="payments")
