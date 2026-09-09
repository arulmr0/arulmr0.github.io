# ADR-0002: SQLAlchemy ORM with SQLite by default

**Status**: accepted

## Context
The system must run on a single laptop or a small VPS with no database administrator, but
should not lock the business into a toy database.

## Decision
Use SQLAlchemy 2.0 (typed declarative models). Default to SQLite with foreign keys enabled;
allow any supported backend through `HFS_DATABASE_URL`.

## Consequences
- Zero-install start; `pytest` uses in-memory SQLite.
- Numeric columns: money is stored as integers (ADR-0004) and quantities as floats, so the
  SQLite/PostgreSQL behaviour is identical.
- Adopt Alembic before the first production schema change.
