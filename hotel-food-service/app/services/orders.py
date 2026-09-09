"""Sales orders: lifecycle, billing and inventory consumption.

State machine::

    OPEN --send_to_kitchen--> IN_KITCHEN --serve--> SERVED --pay--> PAID
      |                            |                   |
      +-----------cancel-----------+-------cancel------+--> CANCELLED

Payment is also accepted directly from OPEN or IN_KITCHEN (takeaway / prepaid room service).
Lines can only be changed while the order is OPEN.
Paying an order posts CONSUMPTION movements for every recipe ingredient, atomically.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from app.core.money import percent_of
from app.models.base import utcnow
from app.models.inventory import MovementType
from app.models.order import Order, OrderLine, OrderStatus, Payment
from app.schemas.order import OrderCreate, OrderLineInput, PaymentCreate
from app.services import inventory as inventory_service
from app.services.menu import get_menu_item

_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.OPEN: {OrderStatus.IN_KITCHEN, OrderStatus.CANCELLED},
    OrderStatus.IN_KITCHEN: {OrderStatus.SERVED, OrderStatus.CANCELLED},
    OrderStatus.SERVED: {OrderStatus.CANCELLED},
    OrderStatus.PAID: set(),
    OrderStatus.CANCELLED: set(),
}
_PAYABLE = {OrderStatus.OPEN, OrderStatus.IN_KITCHEN, OrderStatus.SERVED}


def list_orders(db: Session, status: OrderStatus | None = None, limit: int = 200) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.lines), selectinload(Order.payments))
        .order_by(Order.id.desc())
        .limit(limit)
    )
    if status is not None:
        stmt = stmt.where(Order.status == status)
    return list(db.scalars(stmt))


def get_order(db: Session, order_id: int) -> Order:
    order = db.get(
        Order, order_id, options=[selectinload(Order.lines), selectinload(Order.payments)]
    )
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


def create_order(db: Session, data: OrderCreate, user_id: int) -> Order:
    order = Order(
        number="pending", order_type=data.order_type, location=data.location, created_by=user_id
    )
    db.add(order)
    db.flush()
    order.number = f"ORD-{order.id:06d}"
    for line in data.lines:
        _append_line(db, order, line)
    _recalculate(order)
    db.commit()
    return order


def add_line(db: Session, order_id: int, line: OrderLineInput) -> Order:
    order = get_order(db, order_id)
    if order.status != OrderStatus.OPEN:
        raise InvalidTransitionError("Order lines", order.status.value, "modified")
    _append_line(db, order, line)
    _recalculate(order)
    db.commit()
    return order


def remove_line(db: Session, order_id: int, line_id: int) -> Order:
    order = get_order(db, order_id)
    if order.status != OrderStatus.OPEN:
        raise InvalidTransitionError("Order lines", order.status.value, "modified")
    target = next((line for line in order.lines if line.id == line_id), None)
    if target is None:
        raise NotFoundError(f"Line {line_id} not found on {order.number}")
    order.lines.remove(target)
    _recalculate(order)
    db.commit()
    return order


def change_status(db: Session, order_id: int, target: OrderStatus) -> Order:
    order = get_order(db, order_id)
    if target == OrderStatus.PAID:
        raise ValidationError("Use the payment endpoint to mark an order as paid")
    if target not in _TRANSITIONS[order.status]:
        raise InvalidTransitionError("Order", order.status.value, target.value)
    if target == OrderStatus.IN_KITCHEN and not order.lines:
        raise ValidationError("Cannot send an empty order to the kitchen")
    order.status = target
    if target == OrderStatus.CANCELLED:
        order.closed_at = utcnow()
    db.commit()
    return order


def pay(db: Session, order_id: int, data: PaymentCreate, user_id: int) -> Order:
    """Record a payment. When payments cover the total, close the order and consume stock."""
    order = get_order(db, order_id)
    if order.status not in _PAYABLE:
        raise InvalidTransitionError("Order", order.status.value, "paid")
    if not order.lines:
        raise ValidationError("Cannot pay an empty order")

    paid_so_far = sum(p.amount_minor for p in order.payments)
    outstanding = order.total_minor - paid_so_far
    if data.amount_minor > outstanding:
        raise ValidationError(f"Payment exceeds outstanding balance of {outstanding}")

    payment = Payment(
        order_id=order.id, method=data.method, amount_minor=data.amount_minor, received_by=user_id
    )
    db.add(payment)
    order.payments.append(payment)

    if paid_so_far + data.amount_minor == order.total_minor:
        from app.services import reservations as reservation_service

        _consume_inventory(db, order, user_id)
        order.status = OrderStatus.PAID
        order.closed_at = utcnow()
        reservation_service.complete_for_order(db, order)
    db.commit()
    return order


def _append_line(db: Session, order: Order, line: OrderLineInput) -> None:
    item = get_menu_item(db, line.menu_item_id)
    if not item.is_available:
        raise ValidationError(f"'{item.name}' is not available")
    order.lines.append(
        OrderLine(
            menu_item_id=item.id,
            quantity=line.quantity,
            unit_price_minor=item.price_minor,
            notes=line.notes,
        )
    )


def _recalculate(order: Order) -> None:
    order.subtotal_minor = sum(line.line_total_minor for line in order.lines)
    order.tax_minor = percent_of(order.subtotal_minor, get_settings().tax_rate_percent)
    order.total_minor = order.subtotal_minor + order.tax_minor


def _consume_inventory(db: Session, order: Order, user_id: int) -> None:
    """Aggregate ingredient demand across all lines, then post one movement per ingredient."""
    demand: dict[int, float] = {}
    for line in order.lines:
        for recipe_line in line.menu_item.recipe:
            demand[recipe_line.ingredient_id] = (
                demand.get(recipe_line.ingredient_id, 0.0) + recipe_line.quantity * line.quantity
            )
    allow_negative = get_settings().allow_negative_stock
    for ingredient_id, quantity in demand.items():
        ingredient = inventory_service.get_ingredient(db, ingredient_id)
        inventory_service.record_movement(
            db,
            ingredient,
            MovementType.CONSUMPTION,
            -quantity,
            reference_type="order",
            reference_id=order.id,
            user_id=user_id,
            allow_negative=allow_negative,
        )
