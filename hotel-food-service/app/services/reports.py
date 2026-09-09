"""Management reports built with aggregate SQL."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.hr import Employee
from app.models.inventory import MovementType, StockMovement
from app.models.menu import MenuItem
from app.models.order import Order, OrderLine, OrderStatus
from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from app.models.reservation import Reservation, ReservationStatus
from app.models.supplier import Supplier
from app.schemas.reports import DashboardSummary, SalesSummary, SupplierSpend, TopItem
from app.services import inventory as inventory_service


def _window(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise ValidationError("date_to must not be before date_from")
    return datetime.combine(date_from, time.min), datetime.combine(
        date_to + timedelta(days=1), time.min
    )


def sales_summary(db: Session, date_from: date, date_to: date) -> SalesSummary:
    start, end = _window(date_from, date_to)
    paid_filter = (
        Order.status == OrderStatus.PAID,
        Order.closed_at >= start,
        Order.closed_at < end,
    )
    row = db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_minor), 0),
            func.coalesce(func.sum(Order.tax_minor), 0),
            func.coalesce(func.sum(Order.subtotal_minor), 0),
        ).where(*paid_filter)
    ).one()
    orders_paid, gross, tax, net = int(row[0]), int(row[1]), int(row[2]), int(row[3])

    cancelled = db.scalar(
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.CANCELLED, Order.closed_at >= start, Order.closed_at < end
        )
    )

    paid_order_ids = select(Order.id).where(*paid_filter)
    food_cost = db.scalar(
        select(func.coalesce(func.sum(-StockMovement.quantity * StockMovement.unit_cost_minor), 0))
        .where(StockMovement.movement_type == MovementType.CONSUMPTION)
        .where(StockMovement.reference_type == "order")
        .where(StockMovement.reference_id.in_(paid_order_ids))
    )
    food_cost = int(round(food_cost or 0))
    margin = net - food_cost
    return SalesSummary(
        date_from=date_from,
        date_to=date_to,
        orders_paid=orders_paid,
        orders_cancelled=int(cancelled or 0),
        gross_sales_minor=gross,
        tax_collected_minor=tax,
        net_sales_minor=net,
        food_cost_minor=food_cost,
        gross_margin_minor=margin,
        gross_margin_percent=round(margin / net * 100, 2) if net else 0.0,
        average_ticket_minor=gross // orders_paid if orders_paid else 0,
    )


def top_items(db: Session, date_from: date, date_to: date, limit: int = 10) -> list[TopItem]:
    start, end = _window(date_from, date_to)
    revenue = func.sum(OrderLine.quantity * OrderLine.unit_price_minor)
    stmt = (
        select(
            MenuItem.id,
            MenuItem.code,
            MenuItem.name,
            func.sum(OrderLine.quantity).label("qty"),
            revenue.label("revenue"),
        )
        .join(OrderLine, OrderLine.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(Order.status == OrderStatus.PAID, Order.closed_at >= start, Order.closed_at < end)
        .group_by(MenuItem.id)
        .order_by(revenue.desc())
        .limit(limit)
    )
    return [
        TopItem(
            menu_item_id=r[0],
            code=r[1],
            name=r[2],
            quantity_sold=int(r[3]),
            revenue_minor=int(r[4]),
        )
        for r in db.execute(stmt)
    ]


def supplier_spend(db: Session, date_from: date, date_to: date) -> list[SupplierSpend]:
    start, end = _window(date_from, date_to)
    value = func.sum(GoodsReceiptLine.quantity * PurchaseOrderLine.unit_price_minor)
    stmt = (
        select(
            Supplier.id,
            Supplier.name,
            func.count(func.distinct(PurchaseOrder.id)),
            value,
        )
        .join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .join(GoodsReceipt, GoodsReceipt.purchase_order_id == PurchaseOrder.id)
        .join(GoodsReceiptLine, GoodsReceiptLine.receipt_id == GoodsReceipt.id)
        .join(PurchaseOrderLine, PurchaseOrderLine.id == GoodsReceiptLine.purchase_order_line_id)
        .where(GoodsReceipt.received_at >= start, GoodsReceipt.received_at < end)
        .group_by(Supplier.id)
        .order_by(value.desc())
    )
    return [
        SupplierSpend(
            supplier_id=r[0],
            supplier_name=r[1],
            purchase_orders=int(r[2]),
            received_value_minor=int(round(r[3] or 0)),
        )
        for r in db.execute(stmt)
    ]


def dashboard(db: Session, today: date | None = None) -> DashboardSummary:
    today = today or date.today()
    start, end = _window(today, today)
    row = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.status == OrderStatus.PAID, Order.closed_at >= start, Order.closed_at < end
        )
    ).one()
    open_orders = db.scalar(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.IN_KITCHEN, OrderStatus.SERVED])
        )
    )
    open_pos = db.scalar(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(
                [
                    PurchaseOrderStatus.DRAFT,
                    PurchaseOrderStatus.SUBMITTED,
                    PurchaseOrderStatus.PARTIALLY_RECEIVED,
                ]
            )
        )
    )
    active_employees = db.scalar(
        select(func.count(Employee.id)).where(Employee.is_active.is_(True))
    )
    return DashboardSummary(
        today_sales_minor=int(row[1]),
        today_orders=int(row[0]),
        open_orders=int(open_orders or 0),
        low_stock_items=len(inventory_service.low_stock(db)),
        open_purchase_orders=int(open_pos or 0),
        active_employees=int(active_employees or 0),
        inventory_value_minor=inventory_service.valuation(db).total_value_minor,
        reservations_today=int(
            db.scalar(
                select(func.count(Reservation.id)).where(
                    Reservation.reserved_at >= start,
                    Reservation.reserved_at < end,
                    Reservation.status.in_([ReservationStatus.BOOKED, ReservationStatus.SEATED]),
                )
            )
            or 0
        ),
    )
