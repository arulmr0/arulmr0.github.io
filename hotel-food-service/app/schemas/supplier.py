from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    lead_time_days: int = Field(default=2, ge=0, le=365)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    is_active: bool | None = None


class SupplierRead(ORMModel, SupplierBase):
    id: int
    is_active: bool
