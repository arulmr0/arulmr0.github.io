from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.order import OrderStatus
from app.models.user import Role, User
from app.schemas.bill import BillRead
from app.schemas.order import (
    OrderCreate,
    OrderLineInput,
    OrderRead,
    OrderStatusChange,
    PaymentCreate,
)
from app.services import bills as bill_service
from app.services import orders as service

router = APIRouter(prefix="/orders", tags=["sales"])
_front_of_house = require_roles(Role.MANAGER, Role.CASHIER)
_kitchen_or_front = require_roles(Role.MANAGER, Role.CASHIER, Role.CHEF)


@router.get("", response_model=list[OrderRead])
def list_orders(
    status: OrderStatus | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_orders(db, status, limit)


@router.post("", response_model=OrderRead, status_code=201)
def create_order(
    data: OrderCreate, db: Session = Depends(get_db), user: User = Depends(_front_of_house)
):
    return service.create_order(db, data, user.id)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.get_order(db, order_id)


@router.post("/{order_id}/lines", response_model=OrderRead)
def add_line(
    order_id: int,
    line: OrderLineInput,
    db: Session = Depends(get_db),
    _: User = Depends(_front_of_house),
):
    return service.add_line(db, order_id, line)


@router.delete("/{order_id}/lines/{line_id}", response_model=OrderRead)
def remove_line(
    order_id: int, line_id: int, db: Session = Depends(get_db), _: User = Depends(_front_of_house)
):
    return service.remove_line(db, order_id, line_id)


@router.post("/{order_id}/status", response_model=OrderRead)
def change_status(
    order_id: int,
    data: OrderStatusChange,
    db: Session = Depends(get_db),
    _: User = Depends(_kitchen_or_front),
):
    return service.change_status(db, order_id, data.status)


@router.post("/{order_id}/payments", response_model=OrderRead)
def pay(
    order_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_front_of_house),
):
    return service.pay(db, order_id, data, user.id)


@router.get("/{order_id}/bill", response_model=BillRead)
def bill(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Structured bill for receipt printers, e-mail, or other integrations."""
    return bill_service.build_bill(db, order_id)


@router.get("/{order_id}/bill.html", response_class=HTMLResponse)
def bill_html(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Printable bill (80 mm receipt layout)."""
    return HTMLResponse(bill_service.render_html(bill_service.build_bill(db, order_id)))
