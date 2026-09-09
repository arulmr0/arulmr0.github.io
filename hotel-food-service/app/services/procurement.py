"""Procurement: purchase orders and goods receipts.

State machine::

    DRAFT --submit--> SUBMITTED --receive(partial)--> PARTIALLY_RECEIVED --receive(rest)--> RECEIVED
      |                  |                                   |
      +----cancel--------+------------cancel-----------------+--> CANCELLED
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from app.models.inventory import MovementType
from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from app.schemas.procurement import GoodsReceiptCreate, PurchaseOrderCreate
from app.services import inventory as inventory_service
from app.services.suppliers import get_supplier

_RECEIVABLE = {PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.PARTIALLY_RECEIVED}
_CANCELLABLE = {
    PurchaseOrderStatus.DRAFT,
    PurchaseOrderStatus.SUBMITTED,
    PurchaseOrderStatus.PARTIALLY_RECEIVED,
}


def list_purchase_orders(
    db: Session, status: PurchaseOrderStatus | None = None
) -> list[PurchaseOrder]:
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .order_by(PurchaseOrder.id.desc())
    )
    if status is not None:
        stmt = stmt.where(PurchaseOrder.status == status)
    return list(db.scalars(stmt))


def get_purchase_order(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id, options=[selectinload(PurchaseOrder.lines)])
    if po is None:
        raise NotFoundError(f"Purchase order {po_id} not found")
    return po


def create_purchase_order(db: Session, data: PurchaseOrderCreate, user_id: int) -> PurchaseOrder:
    supplier = get_supplier(db, data.supplier_id)
    if not supplier.is_active:
        raise ValidationError(f"Supplier '{supplier.name}' is inactive")

    po = PurchaseOrder(
        number="pending",
        supplier_id=supplier.id,
        expected_date=data.expected_date,
        notes=data.notes,
        created_by=user_id,
    )
    for line in data.lines:
        inventory_service.get_ingredient(db, line.ingredient_id)
        po.lines.append(
            PurchaseOrderLine(
                ingredient_id=line.ingredient_id,
                quantity=line.quantity,
                unit_price_minor=line.unit_price_minor,
            )
        )
    po.total_minor = sum(line.line_total_minor for line in po.lines)
    db.add(po)
    db.flush()
    po.number = f"PO-{po.id:06d}"
    db.commit()
    return po


def submit_purchase_order(db: Session, po_id: int) -> PurchaseOrder:
    po = get_purchase_order(db, po_id)
    if po.status != PurchaseOrderStatus.DRAFT:
        raise InvalidTransitionError("Purchase order", po.status.value, "submitted")
    po.status = PurchaseOrderStatus.SUBMITTED
    db.commit()
    return po


def cancel_purchase_order(db: Session, po_id: int) -> PurchaseOrder:
    po = get_purchase_order(db, po_id)
    if po.status not in _CANCELLABLE:
        raise InvalidTransitionError("Purchase order", po.status.value, "cancelled")
    po.status = PurchaseOrderStatus.CANCELLED
    db.commit()
    return po


def receive_goods(db: Session, po_id: int, data: GoodsReceiptCreate, user_id: int) -> GoodsReceipt:
    """Record a (possibly partial) delivery and post it to the inventory ledger atomically."""
    po = get_purchase_order(db, po_id)
    if po.status not in _RECEIVABLE:
        raise InvalidTransitionError("Purchase order", po.status.value, "received")

    lines_by_id = {line.id: line for line in po.lines}
    receipt = GoodsReceipt(purchase_order_id=po.id, received_by=user_id, notes=data.notes)
    db.add(receipt)
    db.flush()

    seen: set[int] = set()
    for item in data.lines:
        if item.purchase_order_line_id in seen:
            raise ValidationError(f"Line {item.purchase_order_line_id} listed twice")
        seen.add(item.purchase_order_line_id)
        line = lines_by_id.get(item.purchase_order_line_id)
        if line is None:
            raise ValidationError(
                f"Line {item.purchase_order_line_id} does not belong to {po.number}"
            )
        if item.quantity > line.outstanding_quantity + 1e-9:
            raise ValidationError(
                f"Cannot receive {item.quantity:g}; only {line.outstanding_quantity:g} "
                f"outstanding on line {line.id}"
            )
        line.received_quantity += item.quantity
        receipt.lines.append(
            GoodsReceiptLine(purchase_order_line_id=line.id, quantity=item.quantity)
        )
        inventory_service.record_movement(
            db,
            line.ingredient,
            MovementType.RECEIPT,
            item.quantity,
            unit_cost_minor=line.unit_price_minor,
            reference_type="goods_receipt",
            reference_id=receipt.id,
            user_id=user_id,
        )

    fully_received = all(line.outstanding_quantity <= 1e-9 for line in po.lines)
    po.status = (
        PurchaseOrderStatus.RECEIVED if fully_received else PurchaseOrderStatus.PARTIALLY_RECEIVED
    )
    db.commit()
    return receipt


def list_receipts(db: Session, po_id: int) -> list[GoodsReceipt]:
    get_purchase_order(db, po_id)
    stmt = (
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.lines))
        .where(GoodsReceipt.purchase_order_id == po_id)
        .order_by(GoodsReceipt.id)
    )
    return list(db.scalars(stmt))
