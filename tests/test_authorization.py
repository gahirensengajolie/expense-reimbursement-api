"""
Authorization test matrix.

These tests exist specifically to catch IDOR (Insecure Direct Object
Reference) and privilege-escalation bugs: cases where a user can read or
modify data that isn't theirs simply by guessing/incrementing an ID, or by
calling an endpoint their role shouldn't be allowed to call.
"""

from tests.conftest import make_admin, make_manager, register_and_login


def create_expense(client, headers, amount=50.0, category="travel"):
    resp = client.post(
        "/expenses",
        json={"category": category, "amount": amount, "description": "test"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_employee_cannot_see_another_employees_expense(client):
    alice_headers = register_and_login(client, "alice@example.com")
    bob_headers = register_and_login(client, "bob@example.com")

    expense_id = create_expense(client, alice_headers)

    resp = client.get(f"/expenses/{expense_id}", headers=bob_headers)
    # 404, not 403 -- we don't want to confirm the resource even exists
    assert resp.status_code == 404


def test_employee_cannot_edit_another_employees_expense(client):
    alice_headers = register_and_login(client, "alice2@example.com")
    bob_headers = register_and_login(client, "bob2@example.com")

    expense_id = create_expense(client, alice_headers)

    resp = client.patch(
        f"/expenses/{expense_id}",
        json={"amount": 9999},
        headers=bob_headers,
    )
    assert resp.status_code == 404


def test_employee_list_only_returns_own_expenses(client):
    alice_headers = register_and_login(client, "alice3@example.com")
    bob_headers = register_and_login(client, "bob3@example.com")

    create_expense(client, alice_headers)
    create_expense(client, bob_headers)

    resp = client.get("/expenses", headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert all(e["owner_id"] for e in body)


def test_employee_cannot_call_review_endpoint(client, db_session):
    alice_headers = register_and_login(client, "alice4@example.com")
    bob_headers = register_and_login(client, "bob4@example.com")

    expense_id = create_expense(client, alice_headers)
    client.post(f"/expenses/{expense_id}/submit", headers=alice_headers)

    resp = client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": True, "comment": "looks fine"},
        headers=bob_headers,
    )
    assert resp.status_code == 403


def test_manager_cannot_approve_own_expense(client, db_session):
    # Managers can no longer file expenses, but someone promoted after
    # submitting one as an employee must still not be able to approve it.
    manager_headers = register_and_login(client, "manager1@example.com")
    expense_id = create_expense(client, manager_headers)
    client.post(f"/expenses/{expense_id}/submit", headers=manager_headers)
    make_manager(db_session, "manager1@example.com")

    resp = client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": True, "comment": "self-approval attempt"},
        headers=manager_headers,
    )
    assert resp.status_code == 403


def test_manager_can_review_others_expense(client, db_session):
    employee_headers = register_and_login(client, "emp1@example.com")
    manager_headers = register_and_login(client, "manager2@example.com")
    make_manager(db_session, "manager2@example.com")

    expense_id = create_expense(client, employee_headers)
    client.post(f"/expenses/{expense_id}/submit", headers=employee_headers)

    resp = client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": True, "comment": "approved"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_only_admin_can_reimburse(client, db_session):
    employee_headers = register_and_login(client, "emp2@example.com")
    manager_headers = register_and_login(client, "manager3@example.com")
    make_manager(db_session, "manager3@example.com")

    expense_id = create_expense(client, employee_headers)
    client.post(f"/expenses/{expense_id}/submit", headers=employee_headers)
    client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": True, "comment": "ok"},
        headers=manager_headers,
    )

    resp = client.post(f"/expenses/{expense_id}/reimburse", headers=manager_headers)
    assert resp.status_code == 403


def test_employee_cannot_access_admin_endpoints(client):
    employee_headers = register_and_login(client, "emp3@example.com")
    resp = client.get("/admin/users", headers=employee_headers)
    assert resp.status_code == 403


def test_admin_cannot_change_own_role(client, db_session):
    admin_headers = register_and_login(client, "admin1@example.com")
    make_admin(db_session, "admin1@example.com")

    from app.models.user import User

    admin_user = db_session.query(User).filter(User.email == "admin1@example.com").first()

    resp = client.patch(
        f"/admin/users/{admin_user.id}/role",
        json={"role": "employee"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
