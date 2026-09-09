from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.procurement import PurchaseOrderStatus
from app.models.user import Role, User
from app.schemas.procurement import (
    GoodsReceiptCreate,
    GoodsReceiptRead,
    PurchaseOrderCreate,
    PurchaseOrderRead,
)
from app.services import procurement as service

router = APIRouter(prefix="/purchase-orders", tags=["supply chain"])
_buyer = require_roles(Role.MANAGER, Role.STOREKEEPER)


@router.get("", response_model=list[PurchaseOrderRead])
def list_purchase_orders(
    status: PurchaseOrderStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_purchase_orders(db, status)


@router.post("", response_model=PurchaseOrderRead, status_code=201)
def create_purchase_order(
    data: PurchaseOrderCreate, db: Session = Depends(get_db), user: User = Depends(_buyer)
):
    return service.create_purchase_order(db, data, user.id)


@router.get("/{po_id}", response_model=PurchaseOrderRead)
def get_purchase_order(
    po_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return service.get_purchase_order(db, po_id)


@router.post("/{po_id}/submit", response_model=PurchaseOrderRead)
def submit(po_id: int, db: Session = Depends(get_db), _: User = Depends(_buyer)):
    return service.submit_purchase_order(db, po_id)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderRead)
def cancel(po_id: int, db: Session = Depends(get_db), _: User = Depends(_buyer)):
    return service.cancel_purchase_order(db, po_id)


@router.post("/{po_id}/receipts", response_model=GoodsReceiptRead, status_code=201)
def receive(
    po_id: int,
    data: GoodsReceiptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_buyer),
):
    return service.receive_goods(db, po_id, data, user.id)


@router.get("/{po_id}/receipts", response_model=list[GoodsReceiptRead])
def list_receipts(po_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.list_receipts(db, po_id)
