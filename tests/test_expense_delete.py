from tests.conftest import make_manager, register_and_login


def create_expense(client, headers, amount=50.0):
    resp = client.post(
        "/expenses",
        json={"category": "travel", "amount": amount, "description": "test"},
        headers=headers,
    )
    return resp.json()["id"]


def test_owner_can_delete_draft_expense(client):
    headers = register_and_login(client, "delowner@example.com")
    expense_id = create_expense(client, headers)

    resp = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert resp.status_code == 204

    # confirm it's actually gone
    resp = client.get(f"/expenses/{expense_id}", headers=headers)
    assert resp.status_code == 404


def test_cannot_delete_submitted_expense(client):
    headers = register_and_login(client, "delsubmit@example.com")
    expense_id = create_expense(client, headers)
    client.post(f"/expenses/{expense_id}/submit", headers=headers)

    resp = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert resp.status_code == 409

    # still there afterward
    resp = client.get(f"/expenses/{expense_id}", headers=headers)
    assert resp.status_code == 200


def test_non_owner_cannot_delete_others_draft(client):
    alice_headers = register_and_login(client, "delalice@example.com")
    bob_headers = register_and_login(client, "delbob@example.com")
    expense_id = create_expense(client, alice_headers)

    resp = client.delete(f"/expenses/{expense_id}", headers=bob_headers)
    # not visible to bob at all -> 404, not 403 (don't reveal existence)
    assert resp.status_code == 404


def test_manager_cannot_delete_employees_draft_either(client, db_session):
    # Drafts are private to their owner: reviewers only see expenses once
    # they are submitted, so a manager cannot even find (let alone delete)
    # someone else's draft -- the API answers 404, not 403.
    employee_headers = register_and_login(client, "delemp@example.com")
    manager_headers = register_and_login(client, "delmanager@example.com")
    make_manager(db_session, "delmanager@example.com")

    expense_id = create_expense(client, employee_headers)

    resp = client.delete(f"/expenses/{expense_id}", headers=manager_headers)
    assert resp.status_code == 404
