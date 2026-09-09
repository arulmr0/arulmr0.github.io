from datetime import date

from tests.conftest import make_employee, make_ingredient, make_menu_item, make_supplier, stock_up


def test_sales_summary_top_items_and_dashboard(manager, cashier):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    stock_up(manager, supplier["id"], rice["id"], qty=10, price=10000)
    plain = make_menu_item(
        manager, code="RICE", price=10000, recipe=[{"ingredient_id": rice["id"], "quantity": 0.25}]
    )
    tea = make_menu_item(manager, code="TEA", price=2000)
    make_employee(manager)

    def sell(lines):
        o = cashier.post("/api/v1/orders", json={"order_type": "dine_in", "lines": lines}).json()
        r = cashier.post(
            f"/api/v1/orders/{o['id']}/payments",
            json={"method": "cash", "amount_minor": o["total_minor"]},
        )
        assert r.status_code == 200, r.text

    sell([{"menu_item_id": plain["id"], "quantity": 2}, {"menu_item_id": tea["id"], "quantity": 1}])
    sell([{"menu_item_id": tea["id"], "quantity": 3}])
    cancelled = cashier.post(
        "/api/v1/orders",
        json={"order_type": "dine_in", "lines": [{"menu_item_id": tea["id"], "quantity": 1}]},
    ).json()
    cashier.post(f"/api/v1/orders/{cancelled['id']}/status", json={"status": "cancelled"})
    cashier.post("/api/v1/orders", json={"order_type": "dine_in"})  # still open

    today = date.today().isoformat()
    s = manager.get("/api/v1/reports/sales", params={"date_from": today, "date_to": today}).json()
    assert s["orders_paid"] == 2 and s["orders_cancelled"] == 1
    assert s["net_sales_minor"] == 22000 + 6000
    assert s["tax_collected_minor"] == 1100 + 300
    assert s["gross_sales_minor"] == 28000 + 1400
    assert s["food_cost_minor"] == 5000  # 0.5 kg x 100.00
    assert s["gross_margin_minor"] == 28000 - 5000

    top = manager.get(
        "/api/v1/reports/top-items", params={"date_from": today, "date_to": today}
    ).json()
    assert top[0]["code"] == "RICE" and top[0]["quantity_sold"] == 2
    assert top[1]["code"] == "TEA" and top[1]["quantity_sold"] == 4

    spend = manager.get(
        "/api/v1/reports/supplier-spend", params={"date_from": today, "date_to": today}
    ).json()
    assert spend == [
        {
            "supplier_id": supplier["id"],
            "supplier_name": "Fresh Farms",
            "purchase_orders": 1,
            "received_value_minor": 100000,
        }
    ]

    d = manager.get("/api/v1/reports/dashboard").json()
    assert d["today_orders"] == 2 and d["open_orders"] == 1 and d["active_employees"] == 1
    assert d["inventory_value_minor"] == 95000

    assert (
        manager.get(
            "/api/v1/reports/sales", params={"date_from": today, "date_to": "2020-01-01"}
        ).status_code
        == 422
    )


def test_reports_are_management_only(cashier):
    assert (
        cashier.get(
            "/api/v1/reports/sales", params={"date_from": "2026-01-01", "date_to": "2026-01-31"}
        ).status_code
        == 403
    )
    assert cashier.get("/api/v1/reports/dashboard").status_code == 200
