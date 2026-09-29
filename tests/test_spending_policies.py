from tests.conftest import register_and_login


def test_expense_within_policy_is_not_flagged(client):
    headers = register_and_login(client, "policy-ok@example.com")
    response = client.post(
        "/expenses",
        json={"category": "meals", "amount": 100, "description": "Team lunch"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["policy_flagged"] is False
    assert body["policy_limit"] == 500.0


def test_expense_over_policy_limit_is_flagged_and_audited(client):
    headers = register_and_login(client, "policy-flagged@example.com")
    response = client.post(
        "/expenses",
        json={"category": "meals", "amount": 750, "description": "Large client dinner"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["policy_flagged"] is True
    assert body["policy_limit"] == 500.0
    assert "exceeds" in body["policy_flag_reason"]

    audit = client.get(f"/expenses/{body['id']}/audit", headers=headers)
    assert audit.status_code == 200
    assert audit.json()[-1]["action"] == "policy_flagged"


def test_unknown_category_uses_other_policy(client):
    headers = register_and_login(client, "policy-other@example.com")
    response = client.post(
        "/expenses",
        json={"category": "miscellaneous", "amount": 1200, "description": "Other item"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["policy_flagged"] is True
    assert response.json()["policy_limit"] == 1000.0
