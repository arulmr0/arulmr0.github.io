from datetime import datetime

from pydantic import BaseModel, Field

from app.models.payroll import PayrollStatus
from app.schemas.common import ORMModel


class PayrollRunCreate(BaseModel):
    period_year: int = Field(ge=2000, le=2100)
    period_month: int = Field(ge=1, le=12)
    working_days: int = Field(ge=1, le=31)


class PayslipRead(ORMModel):
    id: int
    employee_id: int
    days_present: float
    days_absent: float
    hours_worked: float
    overtime_hours: float
    basic_minor: int
    overtime_minor: int
    allowance_minor: int
    gross_minor: int
    absence_deduction_minor: int
    statutory_deduction_minor: int
    advance_deduction_minor: int
    total_deductions_minor: int
    net_minor: int


class PayrollRunRead(ORMModel):
    id: int
    period_year: int
    period_month: int
    working_days: int
    status: PayrollStatus
    total_gross_minor: int
    total_deductions_minor: int
    total_net_minor: int
    created_at: datetime
    finalized_at: datetime | None
    payslips: list[PayslipRead]
