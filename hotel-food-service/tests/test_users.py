import os

from app.core.config import Settings
from app.main import bootstrap_admin
from app.models.user import Role
from tests.conftest import PASSWORD


def _login(client, email, password):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def test_health_reports_setup_required(client, as_role):
    assert client.get("/health").json()["setup_required"] is True
    as_role(Role.ADMIN)
    assert client.get("/health").json()["setup_required"] is False


def test_bootstrap_admin_creates_account_once(engine, client, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    import app.main as main_module

    monkeypatch.setattr(
        main_module, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False)
    )
    settings = Settings(
        _env_file=None, admin_email="owner@example.com", admin_password="Owner-pass-1"
    )
    assert bootstrap_admin(settings) is True
    assert bootstrap_admin(settings) is False  # already exists; password untouched
    assert _login(client, "owner@example.com", "Owner-pass-1").status_code == 200
    assert Settings(_env_file=None).admin_email is None or os.environ.get("HFS_ADMIN_EMAIL")
    assert bootstrap_admin(Settings(_env_file=None, admin_email=None, admin_password=None)) is False


def test_admin_manages_users(admin, client):
    created = admin.post(
        "/api/v1/auth/users",
        json={
            "email": "new@example.com",
            "full_name": "New",
            "password": "Password1",
            "role": "chef",
        },
    ).json()
    uid = created["id"]
    assert (
        admin.patch(f"/api/v1/auth/users/{uid}", json={"role": "manager"}).json()["role"]
        == "manager"
    )

    admin.patch(f"/api/v1/auth/users/{uid}", json={"is_active": False})
    assert _login(client, "new@example.com", "Password1").status_code == 401
    admin.patch(f"/api/v1/auth/users/{uid}", json={"is_active": True})
    assert _login(client, "new@example.com", "Password1").status_code == 200

    admin.post(f"/api/v1/auth/users/{uid}/reset-password", json={"new_password": "Changed-99"})
    assert _login(client, "new@example.com", "Password1").status_code == 401
    assert _login(client, "new@example.com", "Changed-99").status_code == 200

    assert admin.get("/api/v1/auth/users/999").status_code in (404, 405)
    assert admin.patch("/api/v1/auth/users/999", json={"role": "chef"}).status_code == 404


def test_last_admin_is_protected(admin):
    me = admin.get("/api/v1/auth/me").json()
    r = admin.patch(f"/api/v1/auth/users/{me['id']}", json={"role": "manager"})
    assert r.status_code == 422 and "last active administrator" in r.json()["detail"]
    r = admin.patch(f"/api/v1/auth/users/{me['id']}", json={"is_active": False})
    assert r.status_code == 422
    # a second admin makes demotion of the first possible, but self-deactivation still is not
    second = admin.post(
        "/api/v1/auth/users",
        json={
            "email": "a2@example.com",
            "full_name": "A2",
            "password": "Password1",
            "role": "admin",
        },
    ).json()
    assert (
        admin.patch(f"/api/v1/auth/users/{second['id']}", json={"role": "chef"}).status_code == 200
    )
    assert (
        admin.patch(f"/api/v1/auth/users/{second['id']}", json={"role": "admin"}).status_code == 200
    )
    assert (
        admin.patch(f"/api/v1/auth/users/{me['id']}", json={"is_active": False}).status_code == 422
    )


def test_change_own_password(manager, client):
    r = manager.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "Another-pass-1"},
    )
    assert r.status_code == 422
    r = manager.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Another-pass-1"},
    )
    assert r.status_code == 200
    assert _login(client, "manager@example.com", "Another-pass-1").status_code == 200


def test_non_admin_cannot_manage_users(manager, admin):
    me = admin.get("/api/v1/auth/me").json()
    assert manager.get("/api/v1/auth/users").status_code == 403
    assert manager.patch(f"/api/v1/auth/users/{me['id']}", json={"role": "chef"}).status_code == 403
    r = manager.post(
        f"/api/v1/auth/users/{me['id']}/reset-password", json={"new_password": "Hacked-123"}
    )
    assert r.status_code == 403
