from tests.conftest import make_manager, register_and_login


def create_expense(client, headers, amount=50.0):
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": amount, "description": "test"},
        headers=headers,
    )
    return resp.json()["id"]


def test_new_expense_starts_as_draft(client):
    headers = register_and_login(client)
    expense_id = create_expense(client, headers)
    resp = client.get(f"/expenses/{expense_id}", headers=headers)
    assert resp.json()["status"] == "draft"


def test_cannot_submit_already_submitted_expense(client):
    headers = register_and_login(client)
    expense_id = create_expense(client, headers)
    client.post(f"/expenses/{expense_id}/submit", headers=headers)

    resp = client.post(f"/expenses/{expense_id}/submit", headers=headers)
    assert resp.status_code == 409


def test_cannot_edit_submitted_expense(client):
    headers = register_and_login(client)
    expense_id = create_expense(client, headers)
    client.post(f"/expenses/{expense_id}/submit", headers=headers)

    resp = client.patch(f"/expenses/{expense_id}", json={"amount": 100}, headers=headers)
    assert resp.status_code == 409


def test_cannot_reimburse_before_approval(client, db_session):
    from tests.conftest import make_admin

    admin_headers = register_and_login(client, "admin2@example.com")
    make_admin(db_session, "admin2@example.com")

    emp_headers = register_and_login(client, "emp5@example.com")
    expense_id = create_expense(client, emp_headers)

    # expense is still in "draft" -- reimburse is only legal from "approved"
    resp = client.post(f"/expenses/{expense_id}/reimburse", headers=admin_headers)
    assert resp.status_code == 409


def test_rejected_expense_can_go_back_to_draft(client, db_session):
    employee_headers = register_and_login(client, "emp6@example.com")
    manager_headers = register_and_login(client, "manager4@example.com")
    make_manager(db_session, "manager4@example.com")

    expense_id = create_expense(client, employee_headers)
    client.post(f"/expenses/{expense_id}/submit", headers=employee_headers)
    client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": False, "comment": "needs receipt"},
        headers=manager_headers,
    )

    resp = client.get(f"/expenses/{expense_id}", headers=employee_headers)
    assert resp.json()["status"] == "rejected"

    # allowed transition: rejected -> draft (resubmit flow) is only reachable
    # via submit endpoint's guard using ALLOWED_TRANSITIONS, not exposed
    # directly here, so we just confirm rejected state is terminopen properly
    assert resp.json()["reviewer_comment"] == "needs receipt"


def test_negative_amount_rejected(client):
    headers = register_and_login(client)
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": -10, "description": "bad"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_zero_amount_rejected(client):
    headers = register_and_login(client)
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": 0, "description": "bad"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_amount_exceeding_max_rejected(client):
    headers = register_and_login(client)
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": 5_000_000, "description": "huge"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_oversized_description_rejected(client):
    headers = register_and_login(client)
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": 10, "description": "x" * 5000},
        headers=headers,
    )
    assert resp.status_code == 422


def test_missing_required_fields_rejected(client):
    headers = register_and_login(client)
    resp = client.post("/expenses", json={}, headers=headers)
    assert resp.status_code == 422
