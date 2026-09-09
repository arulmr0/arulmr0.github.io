from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services import suppliers as service

router = APIRouter(prefix="/suppliers", tags=["supply chain"])
_writer = require_roles(Role.MANAGER, Role.STOREKEEPER)


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_suppliers(db, include_inactive)


@router.post("", response_model=SupplierRead, status_code=201)
def create_supplier(
    data: SupplierCreate, db: Session = Depends(get_db), _: User = Depends(_writer)
):
    return service.create_supplier(db, data)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return service.get_supplier(db, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_writer),
):
    return service.update_supplier(db, supplier_id, data)
