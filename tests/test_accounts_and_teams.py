import pytest

from app.core.config import settings
from app.models.user import User
from app.services.admin_service import AdminService
from tests.conftest import make_admin, make_manager, register_and_login

PAYLOAD = {"category": "meals", "amount": 40, "description": "lunch"}


def make_admin_headers(client, db_session, email="boss@example.com"):
    headers = register_and_login(client, email)
    make_admin(db_session, email)
    return headers


def user_id(db_session, email):
    return db_session.query(User).filter(User.email == email).one().id


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def file_expense(client, headers, submit=True):
    expense_id = client.post("/expenses", json=PAYLOAD, headers=headers).json()["id"]
    if submit:
        client.post(f"/expenses/{expense_id}/submit", headers=headers)
    return expense_id


# ---- registration ----------------------------------------------------------


def test_self_registration_can_be_disabled(client, monkeypatch):
    assert client.get("/auth/config").json() == {"allow_self_registration": True}

    monkeypatch.setattr(settings, "allow_self_registration", False)
    assert client.get("/auth/config").json() == {"allow_self_registration": False}
    resp = client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "StrongPass123", "full_name": "X"},
    )
    assert resp.status_code == 403


# ---- admin-managed accounts --------------------------------------------------


def test_admin_creates_account_that_must_change_password(client, db_session):
    admin = make_admin_headers(client, db_session)
    resp = client.post(
        "/admin/users",
        json={
            "email": "new.manager@example.com",
            "full_name": "New Manager",
            "role": "manager",
            "password": "Temp-Passw0rd",
        },
        headers=admin,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "manager"
    assert resp.json()["must_change_password"] is True

    tokens = login(client, "new.manager@example.com", "Temp-Passw0rd").json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.json()["must_change_password"] is True


def test_only_admins_can_create_accounts(client, db_session):
    employee = register_and_login(client, "plain@example.com")
    manager = register_and_login(client, "mgr@example.com")
    make_manager(db_session, "mgr@example.com")
    body = {"email": "a@example.com", "full_name": "A", "password": "Temp-Passw0rd"}
    assert client.post("/admin/users", json=body, headers=employee).status_code == 403
    assert client.post("/admin/users", json=body, headers=manager).status_code == 403


def test_create_account_validation(client, db_session):
    admin = make_admin_headers(client, db_session)
    register_and_login(client, "emp@example.com")
    base = {"full_name": "N", "password": "Temp-Passw0rd"}

    dup = client.post("/admin/users", json={**base, "email": "emp@example.com"}, headers=admin)
    assert dup.status_code == 400

    # a manager can't themselves be assigned to a manager
    mgr = client.post(
        "/admin/users", json={**base, "email": "m@example.com", "role": "manager"}, headers=admin
    ).json()
    bad = client.post(
        "/admin/users",
        json={**base, "email": "m2@example.com", "role": "manager", "manager_id": mgr["id"]},
        headers=admin,
    )
    assert bad.status_code == 400

    # manager_id must point at a manager, not an employee
    not_a_manager = client.post(
        "/admin/users",
        json={
            **base,
            "email": "e2@example.com",
            "manager_id": user_id(db_session, "emp@example.com"),
        },
        headers=admin,
    )
    assert not_a_manager.status_code == 400


def test_disabled_account_cannot_sign_in_or_use_existing_token(client, db_session):
    admin = make_admin_headers(client, db_session)
    employee = register_and_login(client, "leaver@example.com")
    uid = user_id(db_session, "leaver@example.com")

    resp = client.patch(f"/admin/users/{uid}", json={"is_active": False}, headers=admin)
    assert resp.status_code == 200 and resp.json()["is_active"] is False

    assert login(client, "leaver@example.com", "StrongPass123").status_code == 403
    assert client.get("/expenses", headers=employee).status_code == 401

    client.patch(f"/admin/users/{uid}", json={"is_active": True}, headers=admin)
    assert login(client, "leaver@example.com", "StrongPass123").status_code == 200


def test_admin_cannot_demote_or_disable_themselves(client, db_session):
    admin = make_admin_headers(client, db_session)
    me = user_id(db_session, "boss@example.com")
    assert (
        client.patch(f"/admin/users/{me}", json={"role": "employee"}, headers=admin).status_code
        == 400
    )
    assert (
        client.patch(f"/admin/users/{me}", json={"is_active": False}, headers=admin).status_code
        == 400
    )


# ---- passwords ---------------------------------------------------------------


def test_change_password(client, db_session):
    admin = make_admin_headers(client, db_session)
    client.post(
        "/admin/users",
        json={"email": "p@example.com", "full_name": "P", "password": "Temp-Passw0rd"},
        headers=admin,
    )
    token = login(client, "p@example.com", "Temp-Passw0rd").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    wrong = client.post(
        "/auth/change-password",
        json={"current_password": "nope-nope", "new_password": "Brand-New-Pass1"},
        headers=headers,
    )
    assert wrong.status_code == 400
    same = client.post(
        "/auth/change-password",
        json={"current_password": "Temp-Passw0rd", "new_password": "Temp-Passw0rd"},
        headers=headers,
    )
    assert same.status_code == 400

    ok = client.post(
        "/auth/change-password",
        json={"current_password": "Temp-Passw0rd", "new_password": "Brand-New-Pass1"},
        headers=headers,
    )
    assert ok.status_code == 200 and ok.json()["must_change_password"] is False
    assert login(client, "p@example.com", "Temp-Passw0rd").status_code == 401
    assert login(client, "p@example.com", "Brand-New-Pass1").status_code == 200


def test_change_password_requires_sign_in(client):
    resp = client.post(
        "/auth/change-password", json={"current_password": "a", "new_password": "bbbbbbbb"}
    )
    assert resp.status_code == 401


def test_admin_can_reset_a_forgotten_password(client, db_session):
    admin = make_admin_headers(client, db_session)
    register_and_login(client, "forgot@example.com")
    uid = user_id(db_session, "forgot@example.com")

    resp = client.post(
        f"/admin/users/{uid}/reset-password", json={"password": "Reset-Passw0rd"}, headers=admin
    )
    assert resp.status_code == 200 and resp.json()["must_change_password"] is True
    assert login(client, "forgot@example.com", "StrongPass123").status_code == 401
    assert login(client, "forgot@example.com", "Reset-Passw0rd").status_code == 200


# ---- first admin bootstrap -----------------------------------------------------


def test_first_admin_is_created_once(db_session):
    service = AdminService(db_session)
    admin = service.ensure_first_admin("root@example.com", "LongPassw0rd")
    assert admin.role.value == "admin" and admin.must_change_password is True
    # already have an admin -> nothing happens, even with a different email
    assert service.ensure_first_admin("other@example.com", "LongPassw0rd") is None
    assert db_session.query(User).count() == 1


def test_first_admin_rejects_short_password(db_session):
    with pytest.raises(RuntimeError):
        AdminService(db_session).ensure_first_admin("root@example.com", "short")


# ---- teams and visibility --------------------------------------------------------


@pytest.fixture
def company(client, db_session):
    """Two managers, three employees: e1 -> m1, e2 -> m2, e3 unassigned."""
    admin = make_admin_headers(client, db_session)
    heads = {}
    for name in ("m1", "m2"):
        heads[name] = register_and_login(client, f"{name}@example.com", full_name=name.upper())
        make_manager(db_session, f"{name}@example.com")
    for name in ("e1", "e2", "e3"):
        heads[name] = register_and_login(client, f"{name}@example.com", full_name=name.upper())
    for emp, mgr in (("e1", "m1"), ("e2", "m2")):
        resp = client.patch(
            f"/admin/users/{user_id(db_session, f'{emp}@example.com')}",
            json={"manager_id": user_id(db_session, f"{mgr}@example.com")},
            headers=admin,
        )
        assert resp.status_code == 200
    ids = {name: file_expense(client, heads[name]) for name in ("e1", "e2", "e3")}
    return {"admin": admin, "heads": heads, "ids": ids}


def owners(client, headers):
    return sorted(e["owner_name"] for e in client.get("/expenses", headers=headers).json())


def test_manager_sees_own_team_and_unassigned_only(client, company):
    heads = company["heads"]
    assert owners(client, heads["m1"]) == ["E1", "E3"]
    assert owners(client, heads["m2"]) == ["E2", "E3"]
    assert owners(client, company["admin"]) == ["E1", "E2", "E3"]


def test_manager_cannot_open_or_review_another_teams_expense(client, company):
    heads, ids = company["heads"], company["ids"]
    other_team = ids["e2"]
    assert client.get(f"/expenses/{other_team}", headers=heads["m1"]).status_code == 404
    review = {"approve": True, "comment": "ok"}
    assert (
        client.post(f"/expenses/{other_team}/review", json=review, headers=heads["m1"]).status_code
        == 404
    )
    assert (
        client.post(f"/expenses/{other_team}/review", json=review, headers=heads["m2"]).status_code
        == 200
    )


def test_any_manager_can_review_unassigned_employees(client, company):
    review = {"approve": True, "comment": "ok"}
    resp = client.post(
        f"/expenses/{company['ids']['e3']}/review", json=review, headers=company["heads"]["m1"]
    )
    assert resp.status_code == 200


def test_dashboard_is_scoped_to_the_managers_team(client, company):
    heads = company["heads"]
    assert client.get("/expenses/summary", headers=heads["m1"]).json()["total_count"] == 2
    assert client.get("/expenses/summary", headers=company["admin"]).json()["total_count"] == 3


def test_drafts_stay_private_to_their_owner(client, company):
    heads = company["heads"]
    draft_id = file_expense(client, heads["e1"], submit=False)
    assert client.get(f"/expenses/{draft_id}", headers=heads["e1"]).status_code == 200
    for viewer in (heads["m1"], company["admin"]):
        assert client.get(f"/expenses/{draft_id}", headers=viewer).status_code == 404
        listed = [e["id"] for e in client.get("/expenses", headers=viewer).json()]
        assert draft_id not in listed


def test_demoting_a_manager_returns_their_team_to_unassigned(client, db_session, company):
    admin = company["admin"]
    m1 = user_id(db_session, "m1@example.com")
    assert (
        client.patch(f"/admin/users/{m1}", json={"role": "employee"}, headers=admin).status_code
        == 200
    )
    users = {u["email"]: u for u in client.get("/admin/users", headers=admin).json()}
    assert users["e1@example.com"]["manager_id"] is None
    # e1 is now visible to the other manager as an unassigned employee
    assert "E1" in owners(client, company["heads"]["m2"])
