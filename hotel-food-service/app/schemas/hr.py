from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.hr import AttendanceStatus, PayType
from app.schemas.common import ORMModel


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=20)
    full_name: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=60)
    designation: str = Field(min_length=1, max_length=80)
    pay_type: PayType
    base_pay_minor: int = Field(gt=0)
    hired_on: date
    phone: str | None = None
    bank_account: str | None = None
    user_id: int | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    designation: str | None = None
    pay_type: PayType | None = None
    base_pay_minor: int | None = Field(default=None, gt=0)
    phone: str | None = None
    bank_account: str | None = None
    is_active: bool | None = None


class EmployeeRead(ORMModel):
    id: int
    employee_code: str
    full_name: str
    department: str
    designation: str
    pay_type: PayType
    base_pay_minor: int
    hired_on: date
    phone: str | None
    bank_account: str | None
    is_active: bool
    user_id: int | None


class AttendanceMark(BaseModel):
    employee_id: int
    work_date: date
    status: AttendanceStatus
    check_in: datetime | None = None
    check_out: datetime | None = None

    @model_validator(mode="after")
    def _check_times(self) -> "AttendanceMark":
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class AttendanceRead(ORMModel):
    id: int
    employee_id: int
    work_date: date
    status: AttendanceStatus
    check_in: datetime | None
    check_out: datetime | None
    hours_worked: float


class SalaryAdvanceCreate(BaseModel):
    employee_id: int
    amount_minor: int = Field(gt=0)
    given_on: date
    note: str | None = None


class SalaryAdvanceRead(ORMModel):
    id: int
    employee_id: int
    amount_minor: int
    given_on: date
    note: str | None
    recovered_in_run_id: int | None
