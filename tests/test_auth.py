def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "GoodPass123", "full_name": "A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert body["role"] == "employee"  # default role, never trust client input for this
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "password": "GoodPass123", "full_name": "A"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_register_cannot_self_assign_role(client):
    # Even if a malicious client sends a "role" field, it must be ignored.
    resp = client.post(
        "/auth/register",
        json={
            "email": "hacker@example.com",
            "password": "GoodPass123",
            "full_name": "Hacker",
            "role": "admin",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "employee"


def test_register_weak_password_rejected(client):
    resp = client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short", "full_name": "A"},
    )
    assert resp.status_code == 422


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "GoodPass123", "full_name": "B"},
    )
    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "GoodPass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "c@example.com", "password": "GoodPass123", "full_name": "C"},
    )
    resp = client.post("/auth/login", json={"email": "c@example.com", "password": "WrongPass"})
    assert resp.status_code == 401


def test_login_nonexistent_user_same_error_as_wrong_password(client):
    # Guards against user-enumeration: both cases must look identical.
    resp = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever123"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_protected_endpoint_requires_token(client):
    resp = client.get("/expenses")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/expenses", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_login_rate_limited_after_repeated_failures(client):
    client.post(
        "/auth/register",
        json={"email": "brute@example.com", "password": "GoodPass123", "full_name": "D"},
    )
    last_status = None
    for _ in range(7):
        r = client.post("/auth/login", json={"email": "brute@example.com", "password": "wrong"})
        last_status = r.status_code
    # after exceeding 5/minute, slowapi should return 429
    assert last_status == 429
