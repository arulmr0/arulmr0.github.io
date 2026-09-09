"""Table reservations.

State machine::

    BOOKED --seat--> SEATED --(linked order paid)--> COMPLETED
      |                |
      +--cancel/no_show +--cancel--> CANCELLED / NO_SHOW

Seating a reservation opens a dine-in order on the table and links it. Paying that
order completes the reservation (see ``orders.pay``). Two active reservations may not
overlap on the same table.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidTransitionError, NotFoundError
from app.models.order import Order, OrderType
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.order import OrderCreate
from app.schemas.reservation import ReservationCreate, ReservationUpdate

ACTIVE = (ReservationStatus.BOOKED, ReservationStatus.SEATED)
_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.BOOKED: {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW},
    ReservationStatus.SEATED: {ReservationStatus.CANCELLED, ReservationStatus.COMPLETED},
    ReservationStatus.COMPLETED: set(),
    ReservationStatus.CANCELLED: set(),
    ReservationStatus.NO_SHOW: set(),
}


def list_reservations(
    db: Session, on: date | None = None, status: ReservationStatus | None = None
) -> list[Reservation]:
    stmt = select(Reservation).order_by(Reservation.reserved_at, Reservation.id)
    if on is not None:
        start = datetime.combine(on, time.min)
        stmt = stmt.where(Reservation.reserved_at >= start).where(
            Reservation.reserved_at < start + timedelta(days=1)
        )
    if status is not None:
        stmt = stmt.where(Reservation.status == status)
    return list(db.scalars(stmt))


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise NotFoundError(f"Reservation {reservation_id} not found")
    return reservation


def create_reservation(db: Session, data: ReservationCreate, user_id: int) -> Reservation:
    _ensure_table_free(db, data.table_number, data.reserved_at, data.duration_minutes)
    reservation = Reservation(**data.model_dump(), created_by=user_id)
    db.add(reservation)
    db.commit()
    return reservation


def update_reservation(db: Session, reservation_id: int, data: ReservationUpdate) -> Reservation:
    reservation = get_reservation(db, reservation_id)
    if reservation.status not in ACTIVE:
        raise InvalidTransitionError("Reservation", reservation.status.value, "modified")
    changes = data.model_dump(exclude_unset=True)
    table = changes.get("table_number", reservation.table_number)
    start = changes.get("reserved_at", reservation.reserved_at)
    duration = changes.get("duration_minutes", reservation.duration_minutes)
    _ensure_table_free(db, table, start, duration, exclude_id=reservation.id)
    for field, value in changes.items():
        setattr(reservation, field, value)
    db.commit()
    return reservation


def seat(db: Session, reservation_id: int, user_id: int) -> Reservation:
    """Guests arrived: open a dine-in order on the table and link it."""
    from app.services import orders as order_service

    reservation = get_reservation(db, reservation_id)
    if reservation.status != ReservationStatus.BOOKED:
        raise InvalidTransitionError("Reservation", reservation.status.value, "seated")
    order = order_service.create_order(
        db,
        OrderCreate(order_type=OrderType.DINE_IN, location=reservation.table_number),
        user_id,
    )
    reservation.order_id = order.id
    reservation.status = ReservationStatus.SEATED
    db.commit()
    return reservation


def change_status(db: Session, reservation_id: int, target: ReservationStatus) -> Reservation:
    reservation = get_reservation(db, reservation_id)
    if target == ReservationStatus.SEATED:
        raise ConflictError("Use the seat endpoint; it opens the table's order")
    if target not in _TRANSITIONS[reservation.status]:
        raise InvalidTransitionError("Reservation", reservation.status.value, target.value)
    reservation.status = target
    db.commit()
    return reservation


def complete_for_order(db: Session, order: Order) -> None:
    """Called by the sales module when an order is paid. Flushes, does not commit."""
    reservation = db.scalar(select(Reservation).where(Reservation.order_id == order.id))
    if reservation is not None and reservation.status == ReservationStatus.SEATED:
        reservation.status = ReservationStatus.COMPLETED
        db.flush()


def _ensure_table_free(
    db: Session, table: str, start: datetime, duration_minutes: int, exclude_id: int | None = None
) -> None:
    end = start + timedelta(minutes=duration_minutes)
    stmt = (
        select(Reservation)
        .where(Reservation.table_number == table, Reservation.status.in_(ACTIVE))
        .where(Reservation.reserved_at < end)
    )
    if exclude_id is not None:
        stmt = stmt.where(Reservation.id != exclude_id)
    for other in db.scalars(stmt):
        other_end = other.reserved_at + timedelta(minutes=other.duration_minutes)
        if other_end > start:
            raise ConflictError(
                f"Table {table} is already reserved for {other.guest_name} "
                f"{other.reserved_at:%Y-%m-%d %H:%M} to {other_end:%H:%M}"
            )
