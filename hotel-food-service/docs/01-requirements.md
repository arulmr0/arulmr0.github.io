# 1. Software Requirements Specification

## 1.1 Purpose
A single system that runs the day-to-day operations of a hotel food-service business:
buying ingredients from suppliers, tracking stock, engineering the menu, taking and billing
guest orders, managing staff attendance, and paying salaries.

## 1.2 Stakeholders and roles

| Role | Responsibilities in the system |
|------|--------------------------------|
| Owner / Admin | Creates users, sees everything |
| Manager | Full operational control: purchasing, menu, orders, HR, payroll, reports |
| Chef | Maintains recipes and ingredient master, moves orders through the kitchen |
| Cashier | Opens orders, adds items, records payments |
| Storekeeper | Creates purchase orders, receives goods, records wastage / stock counts |
| HR | Employee master, attendance, salary advances |
| Accountant | Payroll runs, financial reports |

## 1.3 Functional requirements

### FR-1 Identity and access
- FR-1.1 Users authenticate with email + password and receive a bearer token.
- FR-1.2 Every endpoint is protected; each role may only perform the actions listed above.
  Admin may do anything.

### FR-2 Supply chain
- FR-2.1 Maintain a supplier directory with contact details and lead time.
- FR-2.2 Maintain an ingredient master with SKU, unit of measure and reorder level.
- FR-2.3 Raise purchase orders (PO) with one or more lines; the PO carries a unique number.
- FR-2.4 A PO moves DRAFT → SUBMITTED → (PARTIALLY_RECEIVED) → RECEIVED, or is CANCELLED
  before it is fully received. Invalid transitions are rejected.
- FR-2.5 Goods can be received in several deliveries. Over-receipt is rejected.
- FR-2.6 Receiving goods increases stock and updates the ingredient's weighted-average cost.

### FR-3 Inventory
- FR-3.1 Every stock change is an immutable ledger entry (receipt, consumption, wastage, adjustment).
- FR-3.2 Storekeepers can record wastage and stock-count adjustments with a note.
- FR-3.3 Stock cannot go negative unless explicitly configured.
- FR-3.4 The system lists ingredients at or below their reorder level with the shortfall.
- FR-3.5 The system reports total inventory value at average cost.

### FR-4 Menu
- FR-4.1 Menu items have a code, category, selling price and availability flag.
- FR-4.2 Each item may carry a recipe: the ingredient quantities one portion consumes.
- FR-4.3 The system computes food cost, gross margin, food-cost % and the number of portions
  current stock can support.

### FR-5 Sales
- FR-5.1 Orders are dine-in, room-service or takeaway and carry a table / room reference.
- FR-5.2 Lines capture the price at the time of sale; changing the menu later does not alter
  past orders.
- FR-5.3 Order lines may only change while the order is OPEN.
- FR-5.4 Orders move OPEN → IN_KITCHEN → SERVED → PAID, or are CANCELLED before payment.
- FR-5.5 Tax is applied at a configurable rate.
- FR-5.6 Payments may be split across methods (cash, card, UPI, room charge). The order
  becomes PAID when payments equal the total; overpayment is rejected.
- FR-5.7 On payment the recipe ingredients are consumed from stock in one atomic transaction.
  If stock is insufficient the payment is refused and nothing is recorded.

### FR-6 Human resources
- FR-6.1 Employee master with code, department, designation, pay type (monthly / hourly),
  base pay and hire date; optionally linked to a system user.
- FR-6.2 Daily attendance per employee: present, absent, half day, leave, holiday, with
  optional clock-in / clock-out. One record per employee per day (re-marking replaces).
- FR-6.3 Salary advances are recorded and recovered from the next finalized payroll.

### FR-7 Payroll
- FR-7.1 One payroll run per calendar month; duplicates are refused.
- FR-7.2 A run computes a payslip for every active employee: basic, overtime, allowance,
  gross, absence deduction, statutory deduction, advance recovery, net.
- FR-7.3 A draft run can be recomputed or deleted; a finalized run is immutable and marks
  which advances it recovered.
- FR-7.4 Net pay is never negative: advances that do not fit roll over.

### FR-8 Reporting
- FR-8.1 Sales summary for a date range: orders, gross / net sales, tax, food cost, margin,
  average ticket.
- FR-8.2 Top-selling menu items by revenue.
- FR-8.3 Supplier spend based on goods actually received.
- FR-8.4 A live dashboard: today's sales, open orders, low stock, open POs, inventory value,
  headcount.

## 1.4 Non-functional requirements

| ID | Requirement | How it is met |
|----|-------------|---------------|
| NFR-1 | Monetary accuracy | All money is integer minor units; rounding is half-up (ADR-0004) |
| NFR-2 | Data integrity | Foreign keys enforced; multi-step operations are single transactions |
| NFR-3 | Security | bcrypt password hashing, signed JWTs, role checks on every route |
| NFR-4 | Auditability | Append-only stock ledger with reference to the originating document |
| NFR-5 | Portability | Runs on SQLite with zero infrastructure; any SQLAlchemy database via one setting |
| NFR-6 | Testability | Pure domain functions + API tests on an in-memory database; CI on every push |
| NFR-7 | Documentation | OpenAPI at `/docs`; this `docs/` folder; ADRs for key decisions |
| NFR-8 | Deployability | Single container image with health check |

## 1.5 Out of scope (this release)
Table reservations, hotel PMS integration for room folios, multi-branch consolidation,
tax filing formats, biometric attendance devices, and e-invoicing. Extension points for these
are noted in `02-architecture.md`.
