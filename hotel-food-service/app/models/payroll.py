import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PayrollStatus(enum.StrEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class PayrollRun(TimestampMixin, Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("period_year", "period_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayrollStatus] = mapped_column(
        Enum(PayrollStatus), default=PayrollStatus.DRAFT, nullable=False
    )
    total_gross_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_deductions_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_net_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime)

    payslips: Mapped[list["Payslip"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Payslip.employee_id"
    )


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("run_id", "employee_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)

    days_present: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    days_absent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hours_worked: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    basic_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overtime_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allowance_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gross_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    absence_deduction_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    statutory_deduction_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    advance_deduction_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_deductions_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped[PayrollRun] = relationship(back_populates="payslips")
    employee = relationship("Employee")
