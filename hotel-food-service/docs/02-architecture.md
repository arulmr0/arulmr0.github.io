# 2. Architecture

## 2.1 Style: modular monolith

One deployable, internally divided into bounded contexts that only talk through their
service functions. This gives a small team one codebase, one database and one transaction
boundary, while keeping module edges clean enough to extract a service later (ADR-0001).

```mermaid
flowchart LR
    Browser[Web client<br/>web/] -->|JSON over HTTPS| API
    subgraph API [FastAPI application]
        direction TB
        R[api/v1 routers<br/>auth · RBAC · validation] --> S
        subgraph S [services - domain logic]
            direction LR
            Proc[procurement] --> Inv[inventory]
            Ord[orders] --> Inv
            Ord --> Menu[menu]
            Menu --> Inv
            Pay[payroll] --> HR[hr]
            Rep[reports] --> Inv
            Rep --> Ord
            Rep --> Proc
        end
        S --> M[SQLAlchemy models]
    end
    M --> DB[(SQLite / PostgreSQL)]
```

## 2.2 Layers

| Layer | Directory | Responsibility | Must not |
|-------|-----------|----------------|----------|
| Presentation | `web/` | Static single-page client | Contain business rules |
| API | `app/api/v1/` | HTTP routing, auth, request/response schemas, role checks | Touch the ORM directly |
| Domain services | `app/services/` | Business rules, state machines, calculations, transactions | Know about HTTP |
| Persistence | `app/models/` | Tables, relationships, constraints | Contain logic beyond simple derived properties |
| Cross-cutting | `app/core/` | Settings, DB session, security, money, exceptions | Import from upper layers |

Dependency direction is strictly downward. Domain exceptions (`core/exceptions.py`) are
raised by services and translated to HTTP status codes by one handler in `main.py`, so
services stay transport-agnostic.

## 2.3 Bounded contexts and their interactions

| Context | Owns | Publishes to others via |
|---------|------|-------------------------|
| Identity | users, roles | `deps.require_roles` |
| Supply chain | suppliers, purchase orders, goods receipts | `inventory.record_movement` |
| Inventory | ingredients, stock ledger, costing | `get_ingredient`, `record_movement`, `low_stock`, `valuation` |
| Menu | menu items, recipes | `get_menu_item`, `food_cost_minor` |
| Sales | orders, lines, payments | `inventory.record_movement` on payment |
| HR | employees, attendance, advances | queried by payroll |
| Payroll | runs, payslips | reads HR; marks advances recovered |
| Reporting | none (read-only) | aggregates every context |

The inventory ledger is the integration point: procurement writes receipts, sales writes
consumption, storekeepers write wastage/adjustments. Nothing updates `quantity_on_hand`
except `record_movement`, so the denormalised balance can always be rebuilt from the ledger.

## 2.4 Transactions and consistency

- A request is a unit of work: `get_db` yields one session; services call `commit()` once
  at the end of a use case.
- Multi-entity operations (goods receipt → N ledger entries; payment → N consumptions →
  status change) run in one transaction. A failure in the middle rolls everything back;
  `test_payment_refused_when_stock_insufficient` proves this.
- Payroll finalisation recomputes before locking so the locked figures are never stale.

## 2.5 State machines

```
PurchaseOrder: DRAFT → SUBMITTED → PARTIALLY_RECEIVED → RECEIVED
               DRAFT / SUBMITTED / PARTIALLY_RECEIVED → CANCELLED

Order:         OPEN → IN_KITCHEN → SERVED → PAID
               OPEN / IN_KITCHEN / SERVED → CANCELLED
               OPEN / IN_KITCHEN → PAID (takeaway or prepaid)

PayrollRun:    DRAFT ⇄ (recompute) → FINALIZED
```

Transitions are tables in the service modules; anything not in the table raises
`InvalidTransitionError` (HTTP 409).

## 2.6 Security

- Passwords: bcrypt, cost configurable (`HFS_BCRYPT_ROUNDS`).
- Sessions: HS256 JWT with expiry; secret from `HFS_SECRET_KEY`. Rotate it to invalidate all
  sessions.
- Authorization: `require_roles(...)` per route; admin is implicitly allowed everywhere.
- Input validation: Pydantic on every request body and query parameter; numeric bounds
  (`gt=0`, `le=12`, ...) live in the schemas.
- Output: HTML in the client is escaped before insertion.

## 2.7 Configuration
Twelve-factor: everything in `app/core/config.py` can be set through `HFS_*` environment
variables or a `.env` file. See `.env.example`.

## 2.8 Persistence and migrations
Development creates tables at start-up. For production, introduce Alembic
(`alembic init migrations`, `target_metadata = Base.metadata`) before the first schema
change so upgrades are versioned. Switching to PostgreSQL is one setting:
`HFS_DATABASE_URL=postgresql+psycopg://user:pass@host/db`.

## 2.9 Extension points
- **Hotel PMS integration**: room-charge payments already carry the room number; post them
  to the folio from `orders.pay` behind an interface.
- **Notifications**: `inventory.low_stock` is the hook for reorder emails or automatic
  draft POs per supplier lead time.
- **Multi-outlet**: add an `outlet_id` to orders, ingredients and employees; every service
  query already goes through one place per entity.
- **Kitchen display**: `GET /orders?status=in_kitchen` polled or pushed over WebSocket.
