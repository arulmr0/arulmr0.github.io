"""Shared fixtures.

Every test gets a private in-memory SQLite database and an authenticated client
per role. The FastAPI dependency ``get_db`` is overridden so the app and the
tests share the same engine.
"""

import os
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("HFS_BCRYPT_ROUNDS", "4")  # fast hashing for tests
os.environ.setdefault("HFS_DATABASE_URL", "sqlite://")

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.user import Role  # noqa: E402
from app.schemas.auth import UserCreate  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

PASSWORD = "Secret123!"


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def client(engine, db) -> Generator[TestClient, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class RoleClient:
    """Thin wrapper that sends the bearer token for a given role."""

    def __init__(self, client: TestClient, token: str, user_id: int):
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}
        self.user_id = user_id

    def __getattr__(self, name):
        method = getattr(self._client, name)

        def _call(*args, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return method(*args, headers=headers, **kwargs)

        return _call


@pytest.fixture
def as_role(client, db):
    def _make(role: Role) -> RoleClient:
        email = f"{role.value}@example.com"
        user = auth_service.create_user(
            db, UserCreate(email=email, full_name=role.value.title(), password=PASSWORD, role=role)
        )
        resp = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
        assert resp.status_code == 200, resp.text
        return RoleClient(client, resp.json()["access_token"], user.id)

    return _make


@pytest.fixture
def admin(as_role) -> RoleClient:
    return as_role(Role.ADMIN)


@pytest.fixture
def manager(as_role) -> RoleClient:
    return as_role(Role.MANAGER)


@pytest.fixture
def cashier(as_role) -> RoleClient:
    return as_role(Role.CASHIER)


# ----- domain helpers used by several test modules -----


def make_supplier(client: RoleClient, name="Fresh Farms") -> dict:
    r = client.post("/api/v1/suppliers", json={"name": name, "lead_time_days": 1})
    assert r.status_code == 201, r.text
    return r.json()


def make_ingredient(client: RoleClient, sku="RICE", name="Rice", unit="kg", reorder=5) -> dict:
    r = client.post(
        "/api/v1/inventory/ingredients",
        json={"sku": sku, "name": name, "unit": unit, "reorder_level": reorder},
    )
    assert r.status_code == 201, r.text
    return r.json()


def stock_up(client: RoleClient, supplier_id: int, ingredient_id: int, qty: float, price: int):
    """Create, submit and fully receive a one-line PO. Returns the PO."""
    r = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "lines": [{"ingredient_id": ingredient_id, "quantity": qty, "unit_price_minor": price}],
        },
    )
    assert r.status_code == 201, r.text
    po = r.json()
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/submit").status_code == 200
    r = client.post(
        f"/api/v1/purchase-orders/{po['id']}/receipts",
        json={"lines": [{"purchase_order_line_id": po["lines"][0]["id"], "quantity": qty}]},
    )
    assert r.status_code == 201, r.text
    return po


def make_menu_item(client: RoleClient, code="BIR", price=30000, recipe=None) -> dict:
    r = client.post(
        "/api/v1/menu/items",
        json={"code": code, "name": code.title(), "price_minor": price, "recipe": recipe or []},
    )
    assert r.status_code == 201, r.text
    return r.json()


def make_employee(client: RoleClient, code="E1", pay_type="monthly", pay=3000000) -> dict:
    r = client.post(
        "/api/v1/hr/employees",
        json={
            "employee_code": code,
            "full_name": f"Employee {code}",
            "department": "kitchen",
            "designation": "Cook",
            "pay_type": pay_type,
            "base_pay_minor": pay,
            "hired_on": date(2024, 1, 1).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()
