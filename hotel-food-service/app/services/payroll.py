"""Payroll engine.

The calculation itself (``compute_payslip``) is a pure function of an employee, a
``PayrollPolicy``, the month's attendance and outstanding advances. That keeps it
unit-testable without a database. ``create_run`` orchestrates the calculation for
every active employee inside one transaction; ``finalize_run`` locks the run and
marks the recovered advances.

Rules
-----
* MONTHLY employees: basic = monthly salary; daily rate = salary / working days.
  Each day marked ABSENT deducts one daily rate; HALF_DAY deducts half.
  Unmarked days are not deducted (attendance is opt-in for salaried staff).
* HOURLY employees: basic = rate x regular hours; no absence deduction.
* Overtime: hours beyond ``standard_hours_per_day`` on any day, paid at
  hourly rate x ``overtime_multiplier``. Hourly rate for monthly staff is
  daily rate / standard hours.
* Allowance = ``allowance_percent`` of basic.
* Statutory deduction = ``statutory_deduction_percent`` of (basic - absence deduction).
* Advances are recovered oldest-first, but never below zero net pay; anything that
  does not fit rolls over to the next run.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, InvalidTransitionError, NotFoundError
from app.core.money import multiply, percent_of
from app.models.base import utcnow
from app.models.hr import Attendance, AttendanceStatus, Employee, PayType, SalaryAdvance
from app.models.payroll import PayrollRun, PayrollStatus, Payslip
from app.schemas.payroll import PayrollRunCreate


@dataclass(frozen=True)
class PayrollPolicy:
    standard_hours_per_day: float
    overtime_multiplier: float
    statutory_deduction_percent: float
    allowance_percent: float

    @classmethod
    def from_settings(cls) -> "PayrollPolicy":
        s = get_settings()
        return cls(
            standard_hours_per_day=s.standard_hours_per_day,
            overtime_multiplier=s.overtime_multiplier,
            statutory_deduction_percent=s.statutory_deduction_percent,
            allowance_percent=s.allowance_percent,
        )


@dataclass
class PayslipCalculation:
    days_present: float = 0.0
    days_absent: float = 0.0
    hours_worked: float = 0.0
    overtime_hours: float = 0.0
    basic_minor: int = 0
    overtime_minor: int = 0
    allowance_minor: int = 0
    gross_minor: int = 0
    absence_deduction_minor: int = 0
    statutory_deduction_minor: int = 0
    advance_deduction_minor: int = 0
    total_deductions_minor: int = 0
    net_minor: int = 0
    recovered_advance_ids: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.recovered_advance_ids is None:
            self.recovered_advance_ids = []


def _div(minor: int, divisor: float) -> int:
    return int((Decimal(minor) / Decimal(str(divisor))).quantize(Decimal("1"), ROUND_HALF_UP))


def compute_payslip(
    employee: Employee,
    policy: PayrollPolicy,
    working_days: int,
    attendance: list[Attendance],
    advances: list[SalaryAdvance],
) -> PayslipCalculation:
    calc = PayslipCalculation()
    std = policy.standard_hours_per_day

    regular_hours = 0.0
    for record in attendance:
        if record.status == AttendanceStatus.PRESENT:
            calc.days_present += 1
        elif record.status == AttendanceStatus.HALF_DAY:
            calc.days_present += 0.5
            calc.days_absent += 0.5
        elif record.status == AttendanceStatus.ABSENT:
            calc.days_absent += 1
        calc.hours_worked += record.hours_worked
        regular_hours += min(record.hours_worked, std)
        calc.overtime_hours += max(record.hours_worked - std, 0.0)

    if employee.pay_type == PayType.MONTHLY:
        calc.basic_minor = employee.base_pay_minor
        daily_rate = _div(employee.base_pay_minor, working_days)
        hourly_rate = _div(daily_rate, std)
        calc.absence_deduction_minor = multiply(daily_rate, calc.days_absent)
    else:
        hourly_rate = employee.base_pay_minor
        calc.basic_minor = multiply(hourly_rate, regular_hours)

    calc.overtime_minor = multiply(hourly_rate, calc.overtime_hours * policy.overtime_multiplier)
    calc.allowance_minor = percent_of(calc.basic_minor, policy.allowance_percent)
    calc.gross_minor = calc.basic_minor + calc.overtime_minor + calc.allowance_minor

    calc.statutory_deduction_minor = percent_of(
        calc.basic_minor - calc.absence_deduction_minor, policy.statutory_deduction_percent
    )

    available = calc.gross_minor - calc.absence_deduction_minor - calc.statutory_deduction_minor
    for advance in sorted(advances, key=lambda a: (a.given_on, a.id)):
        if advance.amount_minor <= available:
            available -= advance.amount_minor
            calc.advance_deduction_minor += advance.amount_minor
            calc.recovered_advance_ids.append(advance.id)

    calc.total_deductions_minor = (
        calc.absence_deduction_minor + calc.statutory_deduction_minor + calc.advance_deduction_minor
    )
    calc.net_minor = calc.gross_minor - calc.total_deductions_minor
    return calc


def period_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def list_runs(db: Session) -> list[PayrollRun]:
    stmt = (
        select(PayrollRun)
        .options(selectinload(PayrollRun.payslips))
        .order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc())
    )
    return list(db.scalars(stmt))


def get_run(db: Session, run_id: int) -> PayrollRun:
    run = db.get(PayrollRun, run_id, options=[selectinload(PayrollRun.payslips)])
    if run is None:
        raise NotFoundError(f"Payroll run {run_id} not found")
    return run


def create_run(db: Session, data: PayrollRunCreate, user_id: int) -> PayrollRun:
    existing = db.scalar(
        select(PayrollRun).where(
            PayrollRun.period_year == data.period_year,
            PayrollRun.period_month == data.period_month,
        )
    )
    if existing is not None:
        raise ConflictError(
            f"Payroll for {data.period_year}-{data.period_month:02d} already exists "
            f"(run {existing.id}, {existing.status.value})"
        )
    run = PayrollRun(
        period_year=data.period_year,
        period_month=data.period_month,
        working_days=data.working_days,
        created_by=user_id,
    )
    db.add(run)
    db.flush()
    _compute_all(db, run)
    db.commit()
    return run


def recompute_run(db: Session, run_id: int) -> PayrollRun:
    run = get_run(db, run_id)
    if run.status != PayrollStatus.DRAFT:
        raise InvalidTransitionError("Payroll run", run.status.value, "recomputed")
    run.payslips.clear()
    db.flush()
    _compute_all(db, run)
    db.commit()
    return run


def finalize_run(db: Session, run_id: int) -> PayrollRun:
    run = get_run(db, run_id)
    if run.status != PayrollStatus.DRAFT:
        raise InvalidTransitionError("Payroll run", run.status.value, "finalized")
    # Recompute so the locked figures reflect the latest attendance, then mark advances.
    run.payslips.clear()
    db.flush()
    recovered = _compute_all(db, run)
    for advance_id in recovered:
        advance = db.get(SalaryAdvance, advance_id)
        advance.recovered_in_run_id = run.id
    run.status = PayrollStatus.FINALIZED
    run.finalized_at = utcnow()
    db.commit()
    return run


def delete_run(db: Session, run_id: int) -> None:
    run = get_run(db, run_id)
    if run.status != PayrollStatus.DRAFT:
        raise InvalidTransitionError("Payroll run", run.status.value, "deleted")
    db.delete(run)
    db.commit()


def _compute_all(db: Session, run: PayrollRun) -> list[int]:
    """Build payslips for every active employee. Returns the advance ids that were recovered."""
    policy = PayrollPolicy.from_settings()
    start, end = period_bounds(run.period_year, run.period_month)
    employees = list(
        db.scalars(
            select(Employee)
            .where(Employee.is_active.is_(True), Employee.hired_on <= end)
            .order_by(Employee.id)
        )
    )
    recovered: list[int] = []
    run.total_gross_minor = run.total_deductions_minor = run.total_net_minor = 0
    for employee in employees:
        attendance = list(
            db.scalars(
                select(Attendance).where(
                    Attendance.employee_id == employee.id,
                    Attendance.work_date >= start,
                    Attendance.work_date <= end,
                )
            )
        )
        advances = list(
            db.scalars(
                select(SalaryAdvance).where(
                    SalaryAdvance.employee_id == employee.id,
                    SalaryAdvance.recovered_in_run_id.is_(None),
                    SalaryAdvance.given_on <= end,
                )
            )
        )
        calc = compute_payslip(employee, policy, run.working_days, attendance, advances)
        recovered.extend(calc.recovered_advance_ids)
        run.payslips.append(
            Payslip(
                employee_id=employee.id,
                days_present=calc.days_present,
                days_absent=calc.days_absent,
                hours_worked=calc.hours_worked,
                overtime_hours=calc.overtime_hours,
                basic_minor=calc.basic_minor,
                overtime_minor=calc.overtime_minor,
                allowance_minor=calc.allowance_minor,
                gross_minor=calc.gross_minor,
                absence_deduction_minor=calc.absence_deduction_minor,
                statutory_deduction_minor=calc.statutory_deduction_minor,
                advance_deduction_minor=calc.advance_deduction_minor,
                total_deductions_minor=calc.total_deductions_minor,
                net_minor=calc.net_minor,
            )
        )
        run.total_gross_minor += calc.gross_minor
        run.total_deductions_minor += calc.total_deductions_minor
        run.total_net_minor += calc.net_minor
    db.flush()
    return recovered
