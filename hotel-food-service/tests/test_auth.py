from app.models.user import Role


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["version"] == "0.2.0"


def test_client_shell_is_never_cached(client):
    for path in ("/", "/static/app.js", "/static/styles.css"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.headers["cache-control"] == "no-cache, must-revalidate", path
    assert "cache-control" not in client.get("/health").headers


def test_login_and_me(as_role):
    admin = as_role(Role.ADMIN)
    r = admin.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_bad_password(client, admin):
    r = client.post(
        "/api/v1/auth/login", data={"username": "admin@example.com", "password": "nope"}
    )
    assert r.status_code == 401


def test_requires_token(client):
    assert client.get("/api/v1/suppliers").status_code == 401


def test_rbac_blocks_wrong_role(cashier):
    r = cashier.post("/api/v1/suppliers", json={"name": "X"})
    assert r.status_code == 403


def test_admin_creates_user_and_duplicate_rejected(admin):
    body = {"email": "new@example.com", "full_name": "New", "password": "Password1", "role": "chef"}
    assert admin.post("/api/v1/auth/users", json=body).status_code == 201
    assert admin.post("/api/v1/auth/users", json=body).status_code == 409


def test_non_admin_cannot_create_user(manager):
    body = {"email": "x@example.com", "full_name": "X", "password": "Password1", "role": "chef"}
    assert manager.post("/api/v1/auth/users", json=body).status_code == 403
