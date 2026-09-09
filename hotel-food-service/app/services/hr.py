"""Human resources: employee master, attendance and salary advances."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.hr import Attendance, AttendanceStatus, Employee, SalaryAdvance
from app.models.user import User
from app.schemas.hr import AttendanceMark, EmployeeCreate, EmployeeUpdate, SalaryAdvanceCreate


def list_employees(db: Session, include_inactive: bool = False) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.employee_code)
    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list(db.scalars(stmt))


def get_employee(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError(f"Employee {employee_id} not found")
    return employee


def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    if db.scalar(select(Employee).where(Employee.employee_code == data.employee_code)):
        raise ConflictError(f"Employee code '{data.employee_code}' already exists")
    if data.user_id is not None:
        if db.get(User, data.user_id) is None:
            raise NotFoundError(f"User {data.user_id} not found")
        if db.scalar(select(Employee).where(Employee.user_id == data.user_id)):
            raise ConflictError(f"User {data.user_id} is already linked to an employee")
    employee = Employee(**data.model_dump())
    db.add(employee)
    db.commit()
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    employee = get_employee(db, employee_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    return employee


def compute_hours(mark: AttendanceMark, standard_hours: float) -> float:
    """Hours credited for a day. Explicit clock times win; otherwise the status decides."""
    if mark.check_in and mark.check_out:
        return round((mark.check_out - mark.check_in).total_seconds() / 3600, 2)
    if mark.status == AttendanceStatus.PRESENT:
        return standard_hours
    if mark.status == AttendanceStatus.HALF_DAY:
        return standard_hours / 2
    return 0.0


def mark_attendance(db: Session, data: AttendanceMark) -> Attendance:
    """Upsert the attendance record for (employee, date)."""
    employee = get_employee(db, data.employee_id)
    if not employee.is_active:
        raise ValidationError(f"Employee {employee.employee_code} is inactive")
    if data.work_date < employee.hired_on:
        raise ValidationError("Attendance date is before the employee's hire date")

    hours = compute_hours(data, get_settings().standard_hours_per_day)
    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == data.employee_id, Attendance.work_date == data.work_date
        )
    )
    if record is None:
        record = Attendance(employee_id=data.employee_id, work_date=data.work_date)
        db.add(record)
    record.status = data.status
    record.check_in = data.check_in
    record.check_out = data.check_out
    record.hours_worked = hours
    db.commit()
    return record


def list_attendance(
    db: Session, employee_id: int | None, date_from: date, date_to: date
) -> list[Attendance]:
    if date_to < date_from:
        raise ValidationError("date_to must not be before date_from")
    stmt = (
        select(Attendance)
        .where(Attendance.work_date >= date_from, Attendance.work_date <= date_to)
        .order_by(Attendance.work_date, Attendance.employee_id)
    )
    if employee_id is not None:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    return list(db.scalars(stmt))


def give_advance(db: Session, data: SalaryAdvanceCreate) -> SalaryAdvance:
    employee = get_employee(db, data.employee_id)
    if not employee.is_active:
        raise ValidationError(f"Employee {employee.employee_code} is inactive")
    advance = SalaryAdvance(**data.model_dump())
    db.add(advance)
    db.commit()
    return advance


def list_advances(db: Session, employee_id: int | None = None) -> list[SalaryAdvance]:
    stmt = select(SalaryAdvance).order_by(SalaryAdvance.given_on.desc())
    if employee_id is not None:
        stmt = stmt.where(SalaryAdvance.employee_id == employee_id)
    return list(db.scalars(stmt))
