from datetime import date

import pytest

from app.models.hr import Attendance, AttendanceStatus, Employee, PayType, SalaryAdvance
from app.services.payroll import PayrollPolicy, compute_payslip
from tests.conftest import make_employee

POLICY = PayrollPolicy(
    standard_hours_per_day=8,
    overtime_multiplier=1.5,
    statutory_deduction_percent=12,
    allowance_percent=10,
)


def _att(status, hours=None):
    if hours is None:
        hours = {AttendanceStatus.PRESENT: 8.0, AttendanceStatus.HALF_DAY: 4.0}.get(status, 0.0)
    return Attendance(work_date=date(2026, 3, 1), status=status, hours_worked=hours)


# ---------- pure calculation ----------


def test_monthly_full_attendance():
    emp = Employee(pay_type=PayType.MONTHLY, base_pay_minor=2_600_000)  # 26,000.00
    calc = compute_payslip(emp, POLICY, 26, [_att(AttendanceStatus.PRESENT)] * 26, [])
    assert calc.basic_minor == 2_600_000
    assert calc.absence_deduction_minor == 0
    assert calc.allowance_minor == 260_000
    assert calc.gross_minor == 2_860_000
    assert calc.statutory_deduction_minor == 312_000
    assert calc.net_minor == 2_860_000 - 312_000


def test_monthly_absence_and_half_day():
    emp = Employee(pay_type=PayType.MONTHLY, base_pay_minor=2_600_000)
    att = [_att(AttendanceStatus.PRESENT)] * 23 + [
        _att(AttendanceStatus.ABSENT),
        _att(AttendanceStatus.ABSENT),
        _att(AttendanceStatus.HALF_DAY),
    ]
    calc = compute_payslip(emp, POLICY, 26, att, [])
    daily = 100_000
    assert calc.days_absent == 2.5
    assert calc.absence_deduction_minor == int(daily * 2.5)
    assert calc.statutory_deduction_minor == int((2_600_000 - 250_000) * 0.12)


def test_monthly_overtime():
    emp = Employee(pay_type=PayType.MONTHLY, base_pay_minor=2_080_000)  # daily 80,000 hourly 10,000
    att = [_att(AttendanceStatus.PRESENT, hours=10)]  # 2 h overtime
    calc = compute_payslip(emp, POLICY, 26, att, [])
    assert calc.overtime_hours == 2
    assert calc.overtime_minor == 10_000 * 2 * 1.5


def test_hourly_employee():
    emp = Employee(pay_type=PayType.HOURLY, base_pay_minor=15_000)
    att = [_att(AttendanceStatus.PRESENT, hours=8)] * 10 + [
        _att(AttendanceStatus.PRESENT, hours=11)
    ]
    calc = compute_payslip(emp, POLICY, 26, att, [])
    assert calc.basic_minor == 15_000 * 88  # 10x8 + 8 regular hours
    assert calc.overtime_minor == 15_000 * 3 * 1.5
    assert calc.absence_deduction_minor == 0


def test_advances_recovered_oldest_first_without_negative_net():
    emp = Employee(pay_type=PayType.MONTHLY, base_pay_minor=1_000_000)
    advances = [
        SalaryAdvance(id=2, amount_minor=800_000, given_on=date(2026, 3, 10)),
        SalaryAdvance(id=1, amount_minor=300_000, given_on=date(2026, 3, 2)),
    ]
    calc = compute_payslip(emp, POLICY, 26, [], advances)
    # available = gross 1,100,000 - statutory 120,000 = 980,000 -> 300k fits, then 800k does not
    assert calc.recovered_advance_ids == [1]
    assert calc.advance_deduction_minor == 300_000
    assert calc.net_minor == 980_000 - 300_000


# ---------- end-to-end through the API ----------


@pytest.fixture
def hr(as_role):
    from app.models.user import Role

    return as_role(Role.HR)


def test_attendance_upsert_and_hours(hr):
    emp = make_employee(hr)
    body = {
        "employee_id": emp["id"],
        "work_date": "2026-03-02",
        "status": "present",
        "check_in": "2026-03-02T09:00:00",
        "check_out": "2026-03-02T19:30:00",
    }
    r = hr.post("/api/v1/hr/attendance", json=body)
    assert r.status_code == 201 and r.json()["hours_worked"] == 10.5
    body["status"] = "half_day"
    body.pop("check_in"), body.pop("check_out")
    assert hr.post("/api/v1/hr/attendance", json=body).json()["hours_worked"] == 4
    listed = hr.get(
        "/api/v1/hr/attendance", params={"date_from": "2026-03-01", "date_to": "2026-03-31"}
    ).json()
    assert len(listed) == 1  # upsert, not duplicate

    bad = {**body, "check_in": "2026-03-02T10:00:00", "check_out": "2026-03-02T09:00:00"}
    assert hr.post("/api/v1/hr/attendance", json=bad).status_code == 422
    before_hire = {**body, "work_date": "2023-12-31"}
    assert hr.post("/api/v1/hr/attendance", json=before_hire).status_code == 422


def test_payroll_run_lifecycle(hr, as_role):
    from app.models.user import Role

    accountant = as_role(Role.ACCOUNTANT)
    cook = make_employee(hr, code="C1", pay_type="monthly", pay=2_600_000)
    waiter = make_employee(hr, code="W1", pay_type="hourly", pay=15_000)
    for day in range(1, 6):
        hr.post(
            "/api/v1/hr/attendance",
            json={"employee_id": cook["id"], "work_date": f"2026-03-0{day}", "status": "present"},
        )
        hr.post(
            "/api/v1/hr/attendance",
            json={"employee_id": waiter["id"], "work_date": f"2026-03-0{day}", "status": "present"},
        )
    hr.post(
        "/api/v1/hr/attendance",
        json={"employee_id": cook["id"], "work_date": "2026-03-06", "status": "absent"},
    )
    hr.post(
        "/api/v1/hr/advances",
        json={"employee_id": cook["id"], "amount_minor": 200_000, "given_on": "2026-03-03"},
    )

    r = accountant.post(
        "/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 3, "working_days": 26}
    )
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["status"] == "draft" and len(run["payslips"]) == 2
    by_emp = {p["employee_id"]: p for p in run["payslips"]}
    assert by_emp[cook["id"]]["days_absent"] == 1
    assert by_emp[cook["id"]]["advance_deduction_minor"] == 200_000
    assert by_emp[waiter["id"]]["basic_minor"] == 15_000 * 40
    assert run["total_net_minor"] == sum(p["net_minor"] for p in run["payslips"])

    # duplicate period refused
    assert (
        accountant.post(
            "/api/v1/payroll/runs",
            json={"period_year": 2026, "period_month": 3, "working_days": 26},
        ).status_code
        == 409
    )

    # attendance changes are picked up on recompute
    hr.post(
        "/api/v1/hr/attendance",
        json={"employee_id": cook["id"], "work_date": "2026-03-06", "status": "present"},
    )
    run = accountant.post(f"/api/v1/payroll/runs/{run['id']}/recompute").json()
    assert {p["employee_id"]: p for p in run["payslips"]}[cook["id"]]["days_absent"] == 0

    run = accountant.post(f"/api/v1/payroll/runs/{run['id']}/finalize").json()
    assert run["status"] == "finalized" and run["finalized_at"]
    advances = hr.get("/api/v1/hr/advances", params={"employee_id": cook["id"]}).json()
    assert advances[0]["recovered_in_run_id"] == run["id"]

    # finalized runs are immutable
    assert accountant.post(f"/api/v1/payroll/runs/{run['id']}/recompute").status_code == 409
    assert accountant.delete(f"/api/v1/payroll/runs/{run['id']}").status_code == 409

    # next month does not deduct the advance again
    r = accountant.post(
        "/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 4, "working_days": 26}
    )
    assert {p["employee_id"]: p for p in r.json()["payslips"]}[cook["id"]][
        "advance_deduction_minor"
    ] == 0
    assert accountant.delete(f"/api/v1/payroll/runs/{r.json()['id']}").status_code == 204


def test_cashier_cannot_see_payroll(cashier):
    assert cashier.get("/api/v1/payroll/runs").status_code == 403
    assert cashier.get("/api/v1/hr/employees").status_code == 403
