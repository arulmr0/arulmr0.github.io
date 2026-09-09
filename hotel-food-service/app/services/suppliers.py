from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def list_suppliers(db: Session, include_inactive: bool = False) -> list[Supplier]:
    stmt = select(Supplier).order_by(Supplier.name)
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    return list(db.scalars(stmt))


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFoundError(f"Supplier {supplier_id} not found")
    return supplier


def create_supplier(db: Session, data: SupplierCreate) -> Supplier:
    if db.scalar(select(Supplier).where(Supplier.name == data.name)):
        raise ConflictError(f"Supplier '{data.name}' already exists")
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    return supplier


def update_supplier(db: Session, supplier_id: int, data: SupplierUpdate) -> Supplier:
    supplier = get_supplier(db, supplier_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    return supplier
