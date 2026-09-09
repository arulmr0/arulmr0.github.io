import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PayType(enum.StrEnum):
    MONTHLY = "monthly"  # base_pay_minor is the monthly salary
    HOURLY = "hourly"  # base_pay_minor is the hourly rate


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)  # kitchen, service, ...
    designation: Mapped[str] = mapped_column(String(80), nullable=False)
    pay_type: Mapped[PayType] = mapped_column(Enum(PayType), nullable=False)
    base_pay_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    hired_on: Mapped[date] = mapped_column(Date, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    bank_account: Mapped[str | None] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    attendance: Mapped[list["Attendance"]] = relationship(back_populates="employee")


class AttendanceStatus(enum.StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    LEAVE = "leave"  # approved paid leave
    HOLIDAY = "holiday"


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "work_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime)
    check_out: Mapped[datetime | None] = mapped_column(DateTime)
    hours_worked: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="attendance")


class SalaryAdvance(Base):
    """Money paid to an employee ahead of payday; recovered in the next finalised payroll run."""

    __tablename__ = "salary_advances"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    given_on: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    recovered_in_run_id: Mapped[int | None] = mapped_column(ForeignKey("payroll_runs.id"))
