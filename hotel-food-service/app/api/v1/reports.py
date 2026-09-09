from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.reports import DashboardSummary, SalesSummary, SupplierSpend, TopItem
from app.services import reports as service

router = APIRouter(prefix="/reports", tags=["reports"])
_management = require_roles(Role.MANAGER, Role.ACCOUNTANT)


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.dashboard(db)


@router.get("/sales", response_model=SalesSummary)
def sales(
    date_from: date, date_to: date, db: Session = Depends(get_db), _: User = Depends(_management)
):
    return service.sales_summary(db, date_from, date_to)


@router.get("/top-items", response_model=list[TopItem])
def top_items(
    date_from: date,
    date_to: date,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(_management),
):
    return service.top_items(db, date_from, date_to, limit)


@router.get("/supplier-spend", response_model=list[SupplierSpend])
def supplier_spend(
    date_from: date, date_to: date, db: Session = Depends(get_db), _: User = Depends(_management)
):
    return service.supplier_spend(db, date_from, date_to)
