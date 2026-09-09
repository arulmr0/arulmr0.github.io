from datetime import date, datetime, timedelta

import pytest

from tests.conftest import make_ingredient, make_menu_item, make_supplier, stock_up

TONIGHT = datetime.combine(date.today(), datetime.min.time()).replace(hour=19, minute=30)


def _booking(client, table="T1", at=TONIGHT, minutes=90, name="Asha Rao", size=4):
    return client.post(
        "/api/v1/reservations",
        json={
            "guest_name": name,
            "guest_phone": "+91 98765 43210",
            "party_size": size,
            "table_number": table,
            "reserved_at": at.isoformat(),
            "duration_minutes": minutes,
        },
    )


def test_create_and_list_by_day(cashier):
    r = _booking(cashier)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "booked"
    today = cashier.get("/api/v1/reservations", params={"on": date.today().isoformat()}).json()
    tomorrow = cashier.get(
        "/api/v1/reservations", params={"on": (date.today() + timedelta(days=1)).isoformat()}
    ).json()
    assert len(today) == 1 and tomorrow == []


def test_overlapping_booking_on_same_table_rejected(cashier):
    assert _booking(cashier, at=TONIGHT, minutes=90).status_code == 201
    # 20:00 overlaps a 19:30 to 21:00 booking
    r = _booking(cashier, at=TONIGHT + timedelta(minutes=30), name="Vikram")
    assert r.status_code == 409
    assert "already reserved" in r.json()["detail"]
    # 21:00 starts exactly when the first ends: allowed
    assert _booking(cashier, at=TONIGHT + timedelta(minutes=90), name="Vikram").status_code == 201
    # same time, different table: allowed
    assert _booking(cashier, table="T2", name="Nia").status_code == 201


def test_cancelled_booking_frees_the_table(cashier):
    first = _booking(cashier).json()
    cashier.post(f"/api/v1/reservations/{first['id']}/status", json={"status": "cancelled"})
    assert _booking(cashier, name="Later guest").status_code == 201


def test_edit_checks_overlap_and_locks_after_terminal_state(cashier):
    a = _booking(cashier, table="T1").json()
    b = _booking(cashier, table="T2").json()
    r = cashier.patch(f"/api/v1/reservations/{b['id']}", json={"table_number": "T1"})
    assert r.status_code == 409
    r = cashier.patch(f"/api/v1/reservations/{b['id']}", json={"party_size": 6})
    assert r.status_code == 200 and r.json()["party_size"] == 6
    cashier.post(f"/api/v1/reservations/{a['id']}/status", json={"status": "no_show"})
    assert (
        cashier.patch(f"/api/v1/reservations/{a['id']}", json={"party_size": 2}).status_code == 409
    )


@pytest.fixture
def stocked_menu(manager):
    supplier = make_supplier(manager)
    rice = make_ingredient(manager)
    stock_up(manager, supplier["id"], rice["id"], qty=10, price=10000)
    return make_menu_item(
        manager, code="RICE", price=10000, recipe=[{"ingredient_id": rice["id"], "quantity": 0.25}]
    )


def test_seat_opens_order_and_payment_completes_reservation(cashier, stocked_menu):
    booking = _booking(cashier, table="T5").json()
    r = cashier.post(f"/api/v1/reservations/{booking['id']}/seat")
    assert r.status_code == 200, r.text
    seated = r.json()
    assert seated["status"] == "seated" and seated["order_id"]
    order = cashier.get(f"/api/v1/orders/{seated['order_id']}").json()
    assert order["order_type"] == "dine_in" and order["location"] == "T5"

    # cannot seat twice, cannot jump to seated via status endpoint
    assert cashier.post(f"/api/v1/reservations/{booking['id']}/seat").status_code == 409
    r = cashier.post(f"/api/v1/reservations/{booking['id']}/status", json={"status": "seated"})
    assert r.status_code == 409

    cashier.post(
        f"/api/v1/orders/{order['id']}/lines",
        json={"menu_item_id": stocked_menu["id"], "quantity": 2},
    )
    order = cashier.get(f"/api/v1/orders/{order['id']}").json()
    cashier.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "card", "amount_minor": order["total_minor"]},
    )
    assert cashier.get(f"/api/v1/reservations/{booking['id']}").json()["status"] == "completed"


def test_chef_cannot_manage_reservations(as_role):
    from app.models.user import Role

    chef = as_role(Role.CHEF)
    assert _booking(chef).status_code == 403
    assert chef.get("/api/v1/reservations").status_code == 200


def test_bill_json_and_html(cashier, stocked_menu):
    booking = _booking(cashier, table="T9", name="<b>Mallory</b> & Co").json()
    seated = cashier.post(f"/api/v1/reservations/{booking['id']}/seat").json()
    oid = seated["order_id"]
    cashier.post(
        f"/api/v1/orders/{oid}/lines", json={"menu_item_id": stocked_menu["id"], "quantity": 3}
    )
    cashier.post(f"/api/v1/orders/{oid}/payments", json={"method": "cash", "amount_minor": 10000})

    bill = cashier.get(f"/api/v1/orders/{oid}/bill").json()
    assert bill["bill_number"].startswith("ORD-")
    assert bill["guest_name"] == "<b>Mallory</b> & Co"
    assert bill["lines"] == [
        {"description": "Rice", "quantity": 3, "unit_price_minor": 10000, "line_total_minor": 30000}
    ]
    assert bill["subtotal_minor"] == 30000 and bill["tax_minor"] == 1500
    assert bill["total_minor"] == 31500
    assert bill["paid_minor"] == 10000 and bill["balance_due_minor"] == 21500
    assert bill["payments"][0]["method"] == "cash"

    html = cashier.get(f"/api/v1/orders/{oid}/bill.html")
    assert html.status_code == 200 and html.headers["content-type"].startswith("text/html")
    body = html.text
    assert bill["bill_number"] in body
    assert "BALANCE DUE" in body and "215.00" in body
    assert "&lt;b&gt;Mallory&lt;/b&gt; &amp; Co" in body  # guest name is escaped
    assert "<b>Mallory</b>" not in body
    assert "Paid by cash" in body

    cashier.post(f"/api/v1/orders/{oid}/payments", json={"method": "upi", "amount_minor": 21500})
    body = cashier.get(f"/api/v1/orders/{oid}/bill.html").text
    assert ">PAID<" in body and "BALANCE DUE" not in body


def test_bill_for_unknown_order(cashier):
    assert cashier.get("/api/v1/orders/999/bill").status_code == 404
    assert cashier.get("/api/v1/orders/999/bill.html").status_code == 404


def test_dashboard_counts_active_reservations_today(cashier, manager):
    a = _booking(cashier, table="T1").json()
    _booking(cashier, table="T2")
    _booking(cashier, table="T3", at=TONIGHT + timedelta(days=1))
    cashier.post(f"/api/v1/reservations/{a['id']}/status", json={"status": "cancelled"})
    assert manager.get("/api/v1/reports/dashboard").json()["reservations_today"] == 1
