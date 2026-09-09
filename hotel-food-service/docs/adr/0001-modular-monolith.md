# ADR-0001: Modular monolith over microservices

**Status**: accepted

## Context
The business is one hotel kitchen with a handful of staff. It needs procurement, inventory,
sales, HR and payroll that share data tightly (a paid order consumes stock; payroll reads
attendance).

## Decision
Build one FastAPI application with explicit module boundaries (`services/*`) and one
database. Modules call each other's service functions, never each other's tables.

## Consequences
- One deploy, one transaction boundary, simple local development.
- Cross-module invariants (order payment + stock consumption) are atomic without sagas.
- If a module needs independent scaling later (for example a kitchen display), its service
  functions are the seam to extract.
