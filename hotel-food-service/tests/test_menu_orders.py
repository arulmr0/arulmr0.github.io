import pytest

from tests.conftest import make_ingredient, make_menu_item, make_supplier, stock_up


@pytest.fixture
def kitchen(manager):
    """Supplier, two stocked ingredients, and a menu item with a recipe."""
    supplier = make_supplier(manager)
    rice = make_ingredient(manager, sku="RICE", name="Rice")
    chicken = make_ingredient(manager, sku="CHK", name="Chicken")
    stock_up(manager, supplier["id"], rice["id"], qty=10, price=9000)  # 90.00 per kg
    stock_up(manager, supplier["id"], chicken["id"], qty=2, price=24000)  # 240.00 per kg
    biryani = make_menu_item(
        manager,
        code="BIR",
        price=30000,
        recipe=[
            {"ingredient_id": rice["id"], "quantity": 0.2},
            {"ingredient_id": chicken["id"], "quantity": 0.2},
        ],
    )
    return {"rice": rice, "chicken": chicken, "biryani": biryani}


def test_menu_costing(manager, kitchen):
    c = manager.get(f"/api/v1/menu/items/{kitchen['biryani']['id']}/costing").json()
    assert c["food_cost_minor"] == 0.2 * 9000 + 0.2 * 24000  # 6600
    assert c["gross_margin_minor"] == 30000 - 6600
    assert c["food_cost_percent"] == 22.0
    assert c["portions_available"] == pytest.approx(10)  # chicken: 2 / 0.2


def test_order_lifecycle_consumes_stock(manager, cashier, kitchen):
    r = cashier.post(
        "/api/v1/orders",
        json={
            "order_type": "dine_in",
            "location": "T1",
            "lines": [{"menu_item_id": kitchen["biryani"]["id"], "quantity": 2}],
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["subtotal_minor"] == 60000
    assert order["tax_minor"] == 3000  # 5 %
    assert order["total_minor"] == 63000

    oid = order["id"]
    assert (
        cashier.post(f"/api/v1/orders/{oid}/status", json={"status": "in_kitchen"}).status_code
        == 200
    )
    # lines are frozen once in the kitchen
    r = cashier.post(
        f"/api/v1/orders/{oid}/lines",
        json={"menu_item_id": kitchen["biryani"]["id"], "quantity": 1},
    )
    assert r.status_code == 409
    assert (
        cashier.post(f"/api/v1/orders/{oid}/status", json={"status": "served"}).status_code == 200
    )
    # cannot jump to paid via status endpoint
    assert cashier.post(f"/api/v1/orders/{oid}/status", json={"status": "paid"}).status_code == 422

    r = cashier.post(
        f"/api/v1/orders/{oid}/payments", json={"method": "cash", "amount_minor": 30000}
    )
    assert r.status_code == 200 and r.json()["status"] == "served"  # partial payment
    r = cashier.post(
        f"/api/v1/orders/{oid}/payments", json={"method": "card", "amount_minor": 40000}
    )
    assert r.status_code == 422  # exceeds outstanding
    r = cashier.post(
        f"/api/v1/orders/{oid}/payments", json={"method": "card", "amount_minor": 33000}
    )
    assert r.status_code == 200 and r.json()["status"] == "paid"

    chicken = manager.get(f"/api/v1/inventory/ingredients/{kitchen['chicken']['id']}").json()
    assert chicken["quantity_on_hand"] == pytest.approx(2 - 0.4)
    rice = manager.get(f"/api/v1/inventory/ingredients/{kitchen['rice']['id']}").json()
    assert rice["quantity_on_hand"] == pytest.approx(10 - 0.4)

    # terminal state: no further changes
    assert (
        cashier.post(f"/api/v1/orders/{oid}/status", json={"status": "cancelled"}).status_code
        == 409
    )


def test_payment_refused_when_stock_insufficient(cashier, kitchen):
    order = cashier.post(
        "/api/v1/orders",
        json={
            "order_type": "takeaway",
            "lines": [{"menu_item_id": kitchen["biryani"]["id"], "quantity": 11}],
        },
    ).json()
    r = cashier.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "cash", "amount_minor": order["total_minor"]},
    )
    assert r.status_code == 409
    assert "Insufficient stock" in r.json()["detail"]
    # transaction rolled back: order still open, no payment recorded
    again = cashier.get(f"/api/v1/orders/{order['id']}").json()
    assert again["status"] == "open" and again["payments"] == []


def test_unavailable_item_and_empty_order_rules(manager, cashier, kitchen):
    item_id = kitchen["biryani"]["id"]
    manager.patch(f"/api/v1/menu/items/{item_id}", json={"is_available": False})
    r = cashier.post(
        "/api/v1/orders",
        json={"order_type": "dine_in", "lines": [{"menu_item_id": item_id, "quantity": 1}]},
    )
    assert r.status_code == 422
    empty = cashier.post("/api/v1/orders", json={"order_type": "dine_in"}).json()
    assert (
        cashier.post(
            f"/api/v1/orders/{empty['id']}/status", json={"status": "in_kitchen"}
        ).status_code
        == 422
    )
    assert (
        cashier.post(
            f"/api/v1/orders/{empty['id']}/payments", json={"method": "cash", "amount_minor": 1}
        ).status_code
        == 422
    )


def test_chef_cannot_take_payment(as_role, kitchen, cashier):
    from app.models.user import Role

    chef = as_role(Role.CHEF)
    order = cashier.post(
        "/api/v1/orders",
        json={
            "order_type": "dine_in",
            "lines": [{"menu_item_id": kitchen["biryani"]["id"], "quantity": 1}],
        },
    ).json()
    assert (
        chef.post(f"/api/v1/orders/{order['id']}/status", json={"status": "in_kitchen"}).status_code
        == 200
    )
    assert (
        chef.post(
            f"/api/v1/orders/{order['id']}/payments", json={"method": "cash", "amount_minor": 1}
        ).status_code
        == 403
    )
