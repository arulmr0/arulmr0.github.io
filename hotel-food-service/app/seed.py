"""Seed a fresh database with demo data for a small hotel restaurant.

Run with ``python -m app.seed``. Idempotent: does nothing if users already exist.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models import Base
from app.models.hr import AttendanceStatus, PayType
from app.models.inventory import Unit
from app.models.order import OrderType, PaymentMethod
from app.models.user import Role, User
from app.schemas.auth import UserCreate
from app.schemas.hr import AttendanceMark, EmployeeCreate
from app.schemas.inventory import IngredientCreate
from app.schemas.menu import MenuItemCreate, RecipeLineInput
from app.schemas.order import OrderCreate, OrderLineInput, PaymentCreate
from app.schemas.procurement import (
    GoodsReceiptCreate,
    GoodsReceiptLineCreate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
)
from app.schemas.reservation import ReservationCreate
from app.schemas.supplier import SupplierCreate
from app.services import auth, hr, inventory, menu, orders, procurement, reservations, suppliers

DEMO_PASSWORD = "Password123"

DEMO_USERS = [
    ("admin@example.com", "System Admin", Role.ADMIN),
    ("manager@example.com", "Priya Manager", Role.MANAGER),
    ("chef@example.com", "Arjun Chef", Role.CHEF),
    ("cashier@example.com", "Meera Cashier", Role.CASHIER),
    ("store@example.com", "Ravi Storekeeper", Role.STOREKEEPER),
    ("hr@example.com", "Anita HR", Role.HR),
    ("accounts@example.com", "Suresh Accountant", Role.ACCOUNTANT),
]


def seed(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        print("Database already seeded; skipping.")
        return

    users = {
        role: auth.create_user(
            db, UserCreate(email=email, full_name=name, password=DEMO_PASSWORD, role=role)
        )
        for email, name, role in DEMO_USERS
    }
    manager = users[Role.MANAGER]

    fresh = suppliers.create_supplier(
        db, SupplierCreate(name="Fresh Farms Produce", contact_name="Kumar", lead_time_days=1)
    )
    dairy = suppliers.create_supplier(
        db, SupplierCreate(name="City Dairy & Poultry", contact_name="Lakshmi", lead_time_days=2)
    )
    dry = suppliers.create_supplier(
        db, SupplierCreate(name="Metro Dry Goods", contact_name="Farooq", lead_time_days=3)
    )

    def ing(sku, name, cat, unit, reorder):
        return inventory.create_ingredient(
            db,
            IngredientCreate(sku=sku, name=name, category=cat, unit=unit, reorder_level=reorder),
        )

    rice = ing("RICE-BAS", "Basmati rice", "dry goods", Unit.KG, 20)
    chicken = ing("CHK-BRST", "Chicken breast", "poultry", Unit.KG, 10)
    paneer = ing("PANEER", "Paneer", "dairy", Unit.KG, 5)
    tomato = ing("TOMATO", "Tomato", "vegetables", Unit.KG, 8)
    onion = ing("ONION", "Onion", "vegetables", Unit.KG, 10)
    oil = ing("OIL-SUN", "Sunflower oil", "dry goods", Unit.L, 10)
    spice = ing("SPICE-MIX", "Garam masala", "spices", Unit.G, 500)
    flour = ing("FLOUR", "Wheat flour", "dry goods", Unit.KG, 15)
    milk = ing("MILK", "Milk", "dairy", Unit.L, 10)
    coffee = ing("COFFEE", "Coffee beans", "beverages", Unit.G, 1000)

    def po(supplier, lines):
        order = procurement.create_purchase_order(
            db,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                expected_date=date.today(),
                lines=[
                    PurchaseOrderLineCreate(ingredient_id=i.id, quantity=q, unit_price_minor=p)
                    for i, q, p in lines
                ],
            ),
            manager.id,
        )
        procurement.submit_purchase_order(db, order.id)
        procurement.receive_goods(
            db,
            order.id,
            GoodsReceiptCreate(
                lines=[
                    GoodsReceiptLineCreate(purchase_order_line_id=line.id, quantity=line.quantity)
                    for line in order.lines
                ]
            ),
            manager.id,
        )
        return order

    po(fresh, [(tomato, 30, 4000), (onion, 40, 3000)])
    po(dairy, [(chicken, 40, 24000), (paneer, 15, 38000), (milk, 60, 5500)])
    po(
        dry,
        [
            (rice, 100, 9000),
            (oil, 40, 14000),
            (spice, 3000, 60),
            (flour, 50, 4200),
            (coffee, 5000, 90),
        ],
    )

    def item(code, name, cat, price, recipe):
        return menu.create_menu_item(
            db,
            MenuItemCreate(
                code=code,
                name=name,
                category=cat,
                price_minor=price,
                recipe=[RecipeLineInput(ingredient_id=i.id, quantity=q) for i, q in recipe],
            ),
        )

    biryani = item(
        "CHK-BIR",
        "Chicken Biryani",
        "main",
        32000,
        [(rice, 0.2), (chicken, 0.18), (onion, 0.08), (oil, 0.03), (spice, 8)],
    )
    paneer_tm = item(
        "PNR-TM",
        "Paneer Tikka Masala",
        "main",
        28000,
        [(paneer, 0.15), (tomato, 0.12), (onion, 0.06), (oil, 0.02), (spice, 6)],
    )
    roti = item("ROTI", "Tandoori Roti", "bread", 4000, [(flour, 0.06), (oil, 0.005)])
    latte = item("LATTE", "Cafe Latte", "beverage", 18000, [(coffee, 18), (milk, 0.2)])

    def sale(order_type, location, lines, method):
        order = orders.create_order(
            db,
            OrderCreate(
                order_type=order_type,
                location=location,
                lines=[OrderLineInput(menu_item_id=i.id, quantity=q) for i, q in lines],
            ),
            users[Role.CASHIER].id,
        )
        orders.pay(
            db,
            order.id,
            PaymentCreate(method=method, amount_minor=order.total_minor),
            users[Role.CASHIER].id,
        )

    sale(OrderType.DINE_IN, "T4", [(biryani, 2), (roti, 4)], PaymentMethod.CARD)
    sale(
        OrderType.ROOM_SERVICE,
        "R204",
        [(paneer_tm, 1), (roti, 2), (latte, 2)],
        PaymentMethod.ROOM_CHARGE,
    )
    sale(OrderType.TAKEAWAY, None, [(latte, 3)], PaymentMethod.UPI)
    orders.create_order(
        db,
        OrderCreate(
            order_type=OrderType.DINE_IN,
            location="T7",
            lines=[OrderLineInput(menu_item_id=biryani.id, quantity=1)],
        ),
        users[Role.CASHIER].id,
    )

    tonight = datetime.combine(date.today(), datetime.min.time())
    for name, phone, size, table, hour in [
        ("Asha Rao", "+91 98765 43210", 4, "T2", 19),
        ("Daniel Okoye", "+91 91234 56780", 2, "T5", 20),
        ("Meenakshi Iyer", None, 6, "T8", 20),
    ]:
        reservations.create_reservation(
            db,
            ReservationCreate(
                guest_name=name,
                guest_phone=phone,
                party_size=size,
                table_number=table,
                reserved_at=tonight.replace(hour=hour, minute=30),
                duration_minutes=90,
            ),
            manager.id,
        )

    staff = [
        ("EMP-001", "Arjun Chef", "kitchen", "Head Chef", PayType.MONTHLY, 4500000, Role.CHEF),
        (
            "EMP-002",
            "Meera Cashier",
            "front office",
            "Cashier",
            PayType.MONTHLY,
            2200000,
            Role.CASHIER,
        ),
        (
            "EMP-003",
            "Ravi Storekeeper",
            "stores",
            "Storekeeper",
            PayType.MONTHLY,
            2000000,
            Role.STOREKEEPER,
        ),
        ("EMP-004", "Deepak Waiter", "service", "Waiter", PayType.HOURLY, 15000, None),
        ("EMP-005", "Sana Steward", "service", "Steward", PayType.HOURLY, 14000, None),
    ]
    employees = []
    for code, name, dept, title, pay_type, pay, role in staff:
        employees.append(
            hr.create_employee(
                db,
                EmployeeCreate(
                    employee_code=code,
                    full_name=name,
                    department=dept,
                    designation=title,
                    pay_type=pay_type,
                    base_pay_minor=pay,
                    hired_on=date.today().replace(day=1) - timedelta(days=90),
                    user_id=users[role].id if role else None,
                ),
            )
        )

    first_of_month = date.today().replace(day=1)
    for offset in range((date.today() - first_of_month).days + 1):
        day = first_of_month + timedelta(days=offset)
        if day.weekday() == 6:
            continue
        for index, employee in enumerate(employees):
            status = AttendanceStatus.PRESENT
            if offset == 3 and index == 1:
                status = AttendanceStatus.ABSENT
            if offset == 5 and index == 3:
                status = AttendanceStatus.HALF_DAY
            hr.mark_attendance(
                db, AttendanceMark(employee_id=employee.id, work_date=day, status=status)
            )

    print("Seeded demo data. Log in with any of:")
    for email, _, role in DEMO_USERS:
        print(f"  {email:28s} {role.value:12s} password: {DEMO_PASSWORD}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    main()
