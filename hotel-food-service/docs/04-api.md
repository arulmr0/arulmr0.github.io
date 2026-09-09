# 4. API reference

Interactive documentation (OpenAPI / Swagger) is served at `/docs` and `/redoc` when the
application runs. All routes are under `/api/v1` and require `Authorization: Bearer <token>`
except `POST /auth/login`.

| Method & path | Roles | Purpose |
|---------------|-------|---------|
| `POST /auth/login` | — | Form login (`username`, `password`) → JWT |
| `GET /auth/me` | any | Current user |
| `POST /auth/users`, `GET /auth/users` | admin | User administration |
| `PATCH /auth/users/{id}` | admin | Change name, role, active flag (last active admin is protected) |
| `POST /auth/users/{id}/reset-password` | admin | Set a new password for a user |
| `POST /auth/change-password` | any | Change own password (requires current password) |
| `GET/POST /suppliers`, `GET/PATCH /suppliers/{id}` | read: any · write: manager, storekeeper | Supplier directory |
| `GET/POST /inventory/ingredients`, `GET/PATCH /inventory/ingredients/{id}` | read: any · write: manager, storekeeper, chef | Item master |
| `POST /inventory/ingredients/{id}/adjust` | manager, storekeeper, chef | Wastage / stock-count adjustment |
| `GET /inventory/movements` | any | Ledger (filter by `ingredient_id`) |
| `GET /inventory/low-stock`, `GET /inventory/valuation` | any | Reorder list, stock value |
| `GET/POST /purchase-orders`, `GET /purchase-orders/{id}` | read: any · write: manager, storekeeper | Purchase orders |
| `POST /purchase-orders/{id}/submit`, `/cancel` | manager, storekeeper | State transitions |
| `POST /purchase-orders/{id}/receipts`, `GET …/receipts` | manager, storekeeper | Goods receipt (partial allowed) |
| `GET/POST /menu/items`, `GET/PATCH /menu/items/{id}` | read: any · write: manager, chef | Menu |
| `PUT /menu/items/{id}/recipe` | manager, chef | Replace recipe |
| `GET /menu/items/{id}/costing` | any | Food cost, margin, portions available |
| `GET/POST /orders`, `GET /orders/{id}` | read: any · write: manager, cashier | Orders |
| `POST /orders/{id}/lines`, `DELETE /orders/{id}/lines/{line_id}` | manager, cashier | Edit lines (OPEN only) |
| `POST /orders/{id}/status` | manager, cashier, chef | Kitchen / service transitions |
| `POST /orders/{id}/payments` | manager, cashier | Record payment; closes order and consumes stock when settled |
| `GET /orders/{id}/bill`, `GET /orders/{id}/bill.html` | any | Bill as JSON / printable 80 mm HTML |
| `GET/POST /reservations`, `GET/PATCH /reservations/{id}` | read: any · write: manager, cashier | Table bookings (list by `on=YYYY-MM-DD`) |
| `POST /reservations/{id}/seat` | manager, cashier | Seat guests: opens a dine-in order on the table |
| `POST /reservations/{id}/status` | manager, cashier | cancelled / no_show / completed |
| `GET/POST /hr/employees`, `GET/PATCH /hr/employees/{id}` | hr, manager (accountant read) | Employee master |
| `POST /hr/attendance`, `GET /hr/attendance` | hr, manager (accountant read) | Attendance upsert / list |
| `POST /hr/advances`, `GET /hr/advances` | hr, manager, accountant | Salary advances |
| `GET/POST /payroll/runs`, `GET /payroll/runs/{id}` | accountant, hr, manager | Payroll runs |
| `POST /payroll/runs/{id}/recompute`, `/finalize`, `DELETE /payroll/runs/{id}` | accountant, hr, manager | Draft lifecycle |
| `GET /reports/dashboard` | any | KPIs |
| `GET /reports/sales`, `/top-items`, `/supplier-spend` | manager, accountant | Date-range reports |

Admin is allowed on every route.

## Error contract
Every error is `{"detail": "..."}` (or a list of field errors for 422 validation failures).

| Status | Meaning |
|--------|---------|
| 401 | Missing / invalid token or bad credentials |
| 403 | Role not permitted |
| 404 | Entity not found |
| 409 | Conflict: duplicate identifier, invalid state transition, insufficient stock |
| 422 | Validation failure (schema or business rule) |

## Example: a purchase cycle with curl

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d 'username=manager@example.com&password=Password123' | jq -r .access_token)
H="Authorization: Bearer $TOKEN"

curl -s -H "$H" -H 'Content-Type: application/json' localhost:8000/api/v1/purchase-orders \
  -d '{"supplier_id":1,"lines":[{"ingredient_id":1,"quantity":25,"unit_price_minor":9000}]}'
curl -s -X POST -H "$H" localhost:8000/api/v1/purchase-orders/4/submit
curl -s -H "$H" -H 'Content-Type: application/json' localhost:8000/api/v1/purchase-orders/4/receipts \
  -d '{"lines":[{"purchase_order_line_id":11,"quantity":25}]}'
curl -s -H "$H" localhost:8000/api/v1/inventory/low-stock
```
