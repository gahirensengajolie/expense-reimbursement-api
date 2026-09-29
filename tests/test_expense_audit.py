from tests.conftest import make_manager, register_and_login


def test_rejected_expense_can_be_resubmitted_and_audited(client, db_session):
    employee = register_and_login(client, "audit-employee@example.com")
    manager = register_and_login(client, "audit-manager@example.com")
    make_manager(db_session, "audit-manager@example.com")

    created = client.post(
        "/expenses",
        json={"category": "travel", "amount": 125.50, "description": "Client visit"},
        headers=employee,
    )
    assert created.status_code == 201
    expense_id = created.json()["id"]

    assert client.post(f"/expenses/{expense_id}/submit", headers=employee).status_code == 200
    reviewed = client.post(
        f"/expenses/{expense_id}/review",
        json={"approve": False, "comment": "Please attach the receipt"},
        headers=manager,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "rejected"

    resubmitted = client.post(f"/expenses/{expense_id}/resubmit", headers=employee)
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "submitted"

    audit = client.get(f"/expenses/{expense_id}/audit", headers=employee)
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()]
    assert actions == ["created", "submitted", "rejected", "returned_to_draft", "resubmitted"]


def test_employee_cannot_read_another_employees_audit(client):
    owner = register_and_login(client, "audit-owner@example.com")
    stranger = register_and_login(client, "audit-stranger@example.com")
    created = client.post(
        "/expenses",
        json={"category": "meals", "amount": 20, "description": "Lunch"},
        headers=owner,
    )
    expense_id = created.json()["id"]

    response = client.get(f"/expenses/{expense_id}/audit", headers=stranger)
    assert response.status_code == 404
