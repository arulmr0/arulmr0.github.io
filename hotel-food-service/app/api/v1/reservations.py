from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.reservation import ReservationStatus
from app.models.user import Role, User
from app.schemas.reservation import (
    ReservationCreate,
    ReservationRead,
    ReservationStatusChange,
    ReservationUpdate,
)
from app.services import reservations as service

router = APIRouter(prefix="/reservations", tags=["reservations"])
_front_of_house = require_roles(Role.MANAGER, Role.CASHIER)


@router.get("", response_model=list[ReservationRead])
def list_reservations(
    on: date | None = None,
    status: ReservationStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_reservations(db, on, status)


@router.post("", response_model=ReservationRead, status_code=201)
def create_reservation(
    data: ReservationCreate, db: Session = Depends(get_db), user: User = Depends(_front_of_house)
):
    return service.create_reservation(db, data, user.id)


@router.get("/{reservation_id}", response_model=ReservationRead)
def get_reservation(
    reservation_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return service.get_reservation(db, reservation_id)


@router.patch("/{reservation_id}", response_model=ReservationRead)
def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_front_of_house),
):
    return service.update_reservation(db, reservation_id, data)


@router.post("/{reservation_id}/seat", response_model=ReservationRead)
def seat(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(_front_of_house)):
    return service.seat(db, reservation_id, user.id)


@router.post("/{reservation_id}/status", response_model=ReservationRead)
def change_status(
    reservation_id: int,
    data: ReservationStatusChange,
    db: Session = Depends(get_db),
    _: User = Depends(_front_of_house),
):
    return service.change_status(db, reservation_id, data.status)
