import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReservationStatus(enum.StrEnum):
    BOOKED = "booked"
    SEATED = "seated"  # guests arrived; a dine-in order was opened for the table
    COMPLETED = "completed"  # linked order paid
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Reservation(TimestampMixin, Base):
    """A table booking. Times are wall-clock local times of the restaurant."""

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False)
    guest_phone: Mapped[str | None] = mapped_column(String(40))
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    table_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reserved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), default=ReservationStatus.BOOKED, nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), unique=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    order = relationship("Order")
