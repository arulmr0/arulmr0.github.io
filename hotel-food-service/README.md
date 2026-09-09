# Hotel Food Service Management System

End-to-end operations software for a hotel food-service business, built from scratch as a
modular monolith: **supply chain → inventory → menu → orders & billing → HR → payroll →
reports**.

| Module | What it does |
|--------|--------------|
| Supply chain | Suppliers, purchase orders with a state machine, partial goods receipts |
| Inventory | Append-only stock ledger, weighted-average costing, wastage, low-stock alerts, valuation |
| Menu | Items, per-portion recipes, food cost %, margin, portions available from stock |
| Sales | Dine-in / room-service / takeaway orders, kitchen workflow, tax, split payments, automatic stock consumption |
| HR | Employees, daily attendance with clock times, salary advances |
| Payroll | Monthly runs, overtime, allowances, absence and statutory deductions, advance recovery, immutable finalized payslips |
| Reports | Sales summary with food cost & margin, top items, supplier spend, live dashboard |
| Access | 7 roles (admin, manager, chef, cashier, storekeeper, HR, accountant) with JWT auth |

## Quick start

```bash
cd hotel-food-service
python -m venv .venv && source .venv/bin/activate
make install        # pip install -e ".[dev]"
make seed           # demo suppliers, stock, menu, staff, attendance
make dev            # http://localhost:8000  (API docs at /docs)
```

Sign in at `http://localhost:8000` with `manager@example.com` / `Password123`
(other demo roles are printed by `make seed`).

Or with Docker:

```bash
docker compose up --build
docker compose exec api python -m app.seed
```

## Deploy online

The image runs anywhere Docker runs. Two zero-configuration routes are wired up:

**Render (free tier, recommended)**
1. Open https://render.com/deploy?repo=https://github.com/arulmr0/arulmr0.github.io
   and sign in with GitHub.
2. Accept the blueprint from `render.yaml`. It builds the Dockerfile, generates
   `HFS_SECRET_KEY`, enables demo data, and health-checks `/health`.
3. After the first build (3 to 5 minutes) the app is live at
   `https://hotel-food-service.onrender.com` (Render may add a suffix if the name is taken).

Free Render services sleep after 15 minutes without traffic; the first request afterwards
takes about a minute to wake up.

**Hugging Face Space (requires a PRO subscription)**
Docker Spaces are no longer free on Hugging Face; the API answers HTTP 402 without PRO.
If you have PRO: create a *write* token at https://huggingface.co/settings/tokens, add it
as the GitHub Actions secret `HF_TOKEN`, and run the *hotel-food-service deploy* workflow.
The app appears at `https://huggingface.co/spaces/<your-username>/hotel-food-service`.
Optional secrets: `HF_SPACE` to pick another Space name, `HFS_SECRET_KEY` to keep sessions
valid across restarts.

**Important for real business use**: free tiers have no persistent disk, so the SQLite
database is reset when the host restarts or redeploys. Before entering live data, either
attach persistent storage (a Render *disk*, Hugging Face *persistent storage*, a Fly.io
*volume*) and keep `HFS_DATABASE_URL` pointing at it, or set `HFS_DATABASE_URL` to a
managed PostgreSQL instance. Also set `HFS_SEED_ON_START=false` once real data exists.

## Engineering

```bash
make check          # ruff lint + format check + pytest
```

- `docs/01-requirements.md` – requirements specification (roles, FR/NFR)
- `docs/02-architecture.md` – layers, bounded contexts, transactions, state machines, security
- `docs/03-data-model.md` – ER diagram and table notes
- `docs/04-api.md` – endpoint/role matrix and error contract
- `docs/05-testing-and-quality.md` – test strategy, CI, definition of done
- `docs/adr/` – architecture decision records

## Project layout

```
app/
  core/        settings, database session, security, money, domain exceptions
  models/      SQLAlchemy tables (one file per bounded context)
  schemas/     Pydantic request/response contracts
  services/    business rules — the only place that changes data
  api/v1/      FastAPI routers: auth + role checks + validation, no logic
  seed.py      demo data loader
web/           framework-free single-page client
tests/         unit + API tests on an in-memory database
docs/          SRS, architecture, data model, API, ADRs
```

## Configuration
Copy `.env.example` to `.env`. Key settings: `HFS_DATABASE_URL`, `HFS_SECRET_KEY`,
`HFS_CURRENCY`, `HFS_TAX_RATE_PERCENT`, payroll policy percentages, and
`HFS_ALLOW_NEGATIVE_STOCK`.
