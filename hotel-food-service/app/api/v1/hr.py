from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import Role, User
from app.schemas.hr import (
    AttendanceMark,
    AttendanceRead,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    SalaryAdvanceCreate,
    SalaryAdvanceRead,
)
from app.services import hr as service

router = APIRouter(prefix="/hr", tags=["human resources"])
_hr = require_roles(Role.HR, Role.MANAGER)
_hr_or_finance = require_roles(Role.HR, Role.MANAGER, Role.ACCOUNTANT)


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(
    include_inactive: bool = False, db: Session = Depends(get_db), _: User = Depends(_hr_or_finance)
):
    return service.list_employees(db, include_inactive)


@router.post("/employees", response_model=EmployeeRead, status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db), _: User = Depends(_hr)):
    return service.create_employee(db, data)


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int, db: Session = Depends(get_db), _: User = Depends(_hr_or_finance)
):
    return service.get_employee(db, employee_id)


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db), _: User = Depends(_hr)
):
    return service.update_employee(db, employee_id, data)


@router.post("/attendance", response_model=AttendanceRead, status_code=201)
def mark_attendance(data: AttendanceMark, db: Session = Depends(get_db), _: User = Depends(_hr)):
    return service.mark_attendance(db, data)


@router.get("/attendance", response_model=list[AttendanceRead])
def list_attendance(
    date_from: date,
    date_to: date,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(_hr_or_finance),
):
    return service.list_attendance(db, employee_id, date_from, date_to)


@router.post("/advances", response_model=SalaryAdvanceRead, status_code=201)
def give_advance(
    data: SalaryAdvanceCreate, db: Session = Depends(get_db), _: User = Depends(_hr_or_finance)
):
    return service.give_advance(db, data)


@router.get("/advances", response_model=list[SalaryAdvanceRead])
def list_advances(
    employee_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(_hr_or_finance)
):
    return service.list_advances(db, employee_id)
