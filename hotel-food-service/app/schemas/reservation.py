from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.reservation import ReservationStatus
from app.schemas.common import ORMModel


class ReservationCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=120)
    guest_phone: str | None = Field(default=None, max_length=40)
    party_size: int = Field(gt=0, le=100)
    table_number: str = Field(min_length=1, max_length=40)
    reserved_at: datetime
    duration_minutes: int = Field(default=90, ge=15, le=600)
    notes: str | None = Field(default=None, max_length=1000)


class ReservationUpdate(BaseModel):
    guest_name: str | None = Field(default=None, min_length=1, max_length=120)
    guest_phone: str | None = Field(default=None, max_length=40)
    party_size: int | None = Field(default=None, gt=0, le=100)
    table_number: str | None = Field(default=None, min_length=1, max_length=40)
    reserved_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=600)
    notes: str | None = Field(default=None, max_length=1000)


class ReservationStatusChange(BaseModel):
    status: ReservationStatus


class ReservationRead(ORMModel):
    id: int
    guest_name: str
    guest_phone: str | None
    party_size: int
    table_number: str
    reserved_at: datetime
    duration_minutes: int
    status: ReservationStatus
    notes: str | None
    order_id: int | None
    created_at: datetime


class TableAvailability(BaseModel):
    date: date
    table_number: str
    booked_slots: list[tuple[datetime, datetime]]
