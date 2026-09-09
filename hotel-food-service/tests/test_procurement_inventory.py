from tests.conftest import make_ingredient, make_supplier, stock_up


def test_full_purchase_cycle_updates_stock_and_cost(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    po = stock_up(manager, supplier["id"], rice["id"], qty=10, price=9000)

    po_after = manager.get(f"/api/v1/purchase-orders/{po['id']}").json()
    assert po_after["status"] == "received"
    assert po_after["number"].startswith("PO-")
    assert po_after["total_minor"] == 90000

    ing = manager.get(f"/api/v1/inventory/ingredients/{rice['id']}").json()
    assert ing["quantity_on_hand"] == 10
    assert ing["avg_cost_minor"] == 9000

    movements = manager.get("/api/v1/inventory/movements", params={"ingredient_id": rice["id"]})
    assert [m["movement_type"] for m in movements.json()] == ["receipt"]


def test_partial_receipt_and_over_receipt_rejected(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    po = manager.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier["id"],
            "lines": [{"ingredient_id": rice["id"], "quantity": 10, "unit_price_minor": 9000}],
        },
    ).json()
    line_id = po["lines"][0]["id"]
    manager.post(f"/api/v1/purchase-orders/{po['id']}/submit")

    r = manager.post(
        f"/api/v1/purchase-orders/{po['id']}/receipts",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 4}]},
    )
    assert r.status_code == 201
    assert (
        manager.get(f"/api/v1/purchase-orders/{po['id']}").json()["status"] == "partially_received"
    )

    r = manager.post(
        f"/api/v1/purchase-orders/{po['id']}/receipts",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 7}]},
    )
    assert r.status_code == 422
    assert "outstanding" in r.json()["detail"]

    r = manager.post(
        f"/api/v1/purchase-orders/{po['id']}/receipts",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 6}]},
    )
    assert r.status_code == 201
    assert manager.get(f"/api/v1/purchase-orders/{po['id']}").json()["status"] == "received"
    assert len(manager.get(f"/api/v1/purchase-orders/{po['id']}/receipts").json()) == 2


def test_state_machine_rejects_invalid_transitions(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    po = manager.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier["id"],
            "lines": [{"ingredient_id": rice["id"], "quantity": 1, "unit_price_minor": 1}],
        },
    ).json()
    # cannot receive a draft
    r = manager.post(
        f"/api/v1/purchase-orders/{po['id']}/receipts",
        json={"lines": [{"purchase_order_line_id": po["lines"][0]["id"], "quantity": 1}]},
    )
    assert r.status_code == 409
    assert manager.post(f"/api/v1/purchase-orders/{po['id']}/cancel").status_code == 200
    assert manager.post(f"/api/v1/purchase-orders/{po['id']}/submit").status_code == 409


def test_weighted_average_cost(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    stock_up(manager, supplier["id"], rice["id"], qty=10, price=10000)
    stock_up(manager, supplier["id"], rice["id"], qty=10, price=12000)
    ing = manager.get(f"/api/v1/inventory/ingredients/{rice['id']}").json()
    assert ing["quantity_on_hand"] == 20
    assert ing["avg_cost_minor"] == 11000
    assert manager.get("/api/v1/inventory/valuation").json()["total_value_minor"] == 220000


def test_low_stock_and_wastage(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager, reorder=5)
    stock_up(manager, supplier["id"], rice["id"], qty=6, price=100)
    assert manager.get("/api/v1/inventory/low-stock").json() == []

    r = manager.post(
        f"/api/v1/inventory/ingredients/{rice['id']}/adjust",
        json={"movement_type": "wastage", "quantity": -2, "note": "spoiled"},
    )
    assert r.status_code == 201
    low = manager.get("/api/v1/inventory/low-stock").json()
    assert len(low) == 1 and low[0]["shortfall"] == 1

    # wastage must be negative, and stock cannot go below zero
    r = manager.post(
        f"/api/v1/inventory/ingredients/{rice['id']}/adjust",
        json={"movement_type": "wastage", "quantity": 2},
    )
    assert r.status_code == 422
    r = manager.post(
        f"/api/v1/inventory/ingredients/{rice['id']}/adjust",
        json={"movement_type": "adjustment", "quantity": -100},
    )
    assert r.status_code == 409


def test_duplicate_sku_and_supplier(manager):
    make_supplier(manager, "Dup")
    assert manager.post("/api/v1/suppliers", json={"name": "Dup"}).status_code == 409
    make_ingredient(manager, sku="X")
    r = manager.post(
        "/api/v1/inventory/ingredients", json={"sku": "X", "name": "again", "unit": "kg"}
    )
    assert r.status_code == 409
