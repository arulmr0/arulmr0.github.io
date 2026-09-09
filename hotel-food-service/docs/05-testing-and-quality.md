# 5. Testing and quality

## Test pyramid

| Level | Where | What |
|-------|-------|------|
| Unit | `tests/test_money.py`, `tests/test_hr_payroll.py` (top half) | Pure functions: rounding, weighted-average cost, payslip arithmetic. No database. |
| Integration / API | `tests/test_*.py` | Every use case through the HTTP layer against a private in-memory SQLite, including role checks, state-machine rejections and transaction rollback. |
| Data | `tests/test_seed.py` | The demo dataset loads twice without error and leaves consistent stock. |
| Smoke | CI `docker` job | The container image boots and answers `/health`. |

Run locally with `make check` (lint + tests). Tests set `HFS_BCRYPT_ROUNDS=4` so the
suite stays fast; production defaults to 12.

## Static analysis
`ruff` enforces pycodestyle, pyflakes, import order, bugbear, pyupgrade and naming rules
(`pyproject.toml`). Formatting is `ruff format`. CI fails on either.

## Continuous integration
`.github/workflows/hotel-food-service-ci.yml` runs on every push / PR that touches this
directory: lint → tests on Python 3.11 and 3.12 → seed smoke test → Docker build and
health check.

## Definition of done for a change
1. Business rule lives in a service, not a router or the client.
2. A test exercises the happy path and at least one rejection.
3. `make check` is green.
4. `docs/` updated if a requirement, table or endpoint changed; an ADR if a design decision
   was made.

## Known limitations / backlog
- Document numbers (`PO-000001`) derive from the primary key; safe on SQLite, and on
  PostgreSQL as long as one process issues them.
- Attendance for salaried staff is opt-in: unmarked days are not deducted. Enable strict
  mode by marking absences explicitly or extend `compute_payslip`.
- No pagination on list endpoints beyond a `limit`; add cursor pagination once tables grow.
- The client is intentionally framework-free; a larger team may prefer React/Vue with the
  same API.
