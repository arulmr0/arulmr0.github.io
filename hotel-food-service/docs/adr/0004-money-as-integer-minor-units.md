# ADR-0004: Money is stored as integers in minor units

**Status**: accepted

## Context
Floating-point money produces rounding drift in totals, taxes and payroll, and is a common
source of audit disputes.

## Decision
Every monetary column is an integer number of minor units (paise for INR, cents for USD),
named `*_minor`. Conversions and percentage calculations go through `app/core/money.py`,
which uses `Decimal` with ROUND_HALF_UP. Clients convert to major units for display only.

## Consequences
- Sums are exact; `total_net_minor == sum(payslip.net_minor)` holds by construction.
- Prices entered by users are multiplied by 100 in the client (`Math.round(x * 100)`).
- Supporting zero-decimal currencies would require a per-currency exponent; not needed now.
