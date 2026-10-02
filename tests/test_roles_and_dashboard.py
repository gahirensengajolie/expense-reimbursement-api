import pytest

from tests.conftest import make_admin, make_manager, register_and_login

PAYLOAD = {"category": "travel", "amount": 100.0, "description": "trip"}


def _employee(client, email, name="Emp"):
    return register_and_login(client, email, full_name=name)


def _manager(client, db_session, email="mgr@example.com"):
    headers = register_and_login(client, email, full_name="Mgr")
    make_manager(db_session, email)
    return headers


def _admin(client, db_session, email="adm@example.com"):
    headers = register_and_login(client, email, full_name="Adm")
    make_admin(db_session, email)
    return headers


def _submit(client, headers, **overrides):
    created = client.post("/expenses", json={**PAYLOAD, **overrides}, headers=headers)
    assert created.status_code == 201
    expense_id = created.json()["id"]
    assert client.post(f"/expenses/{expense_id}/submit", headers=headers).status_code == 200
    return expense_id


# ---- only employees can create ------------------------------------------


def test_employee_can_create_expense(client):
    resp = client.post("/expenses", json=PAYLOAD, headers=_employee(client, "e1@example.com"))
    assert resp.status_code == 201


def test_manager_cannot_create_expense(client, db_session):
    resp = client.post("/expenses", json=PAYLOAD, headers=_manager(client, db_session))
    assert resp.status_code == 403


def test_admin_cannot_create_expense(client, db_session):
    resp = client.post("/expenses", json=PAYLOAD, headers=_admin(client, db_session))
    assert resp.status_code == 403


def test_demoted_to_manager_stops_being_able_to_create(client, db_session):
    headers = _employee(client, "e2@example.com")
    assert client.post("/expenses", json=PAYLOAD, headers=headers).status_code == 201
    make_manager(db_session, "e2@example.com")
    assert client.post("/expenses", json=PAYLOAD, headers=headers).status_code == 403


# ---- reviewers can see who submitted -------------------------------------


def test_expense_includes_owner_name(client, db_session):
    emp = _employee(client, "e3@example.com", name="Amina Uwase")
    expense_id = _submit(client, emp)
    mgr = _manager(client, db_session)
    body = client.get(f"/expenses/{expense_id}", headers=mgr).json()
    assert body["owner_name"] == "Amina Uwase"


# ---- summary endpoint -----------------------------------------------------


def test_summary_forbidden_for_employee(client):
    resp = client.get("/expenses/summary", headers=_employee(client, "e4@example.com"))
    assert resp.status_code == 403


def test_summary_requires_auth(client):
    assert client.get("/expenses/summary").status_code == 401


@pytest.mark.parametrize("who", ["manager", "admin"])
def test_summary_allowed_for_manager_and_admin(client, db_session, who):
    headers = _manager(client, db_session) if who == "manager" else _admin(client, db_session)
    resp = client.get("/expenses/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 0
    assert body["approval_rate"] is None
    assert len(body["by_month"]) == 6


def test_summary_numbers(client, db_session):
    alice = _employee(client, "alice@example.com", name="Alice")
    bob = _employee(client, "bob@example.com", name="Bob")
    mgr = _manager(client, db_session)
    adm = _admin(client, db_session)

    _submit(client, alice, category="travel", amount=100)  # stays submitted
    approved = _submit(client, alice, category="meals", amount=50)  # -> approved
    paid = _submit(client, bob, category="travel", amount=200)  # -> reimbursed
    rejected = _submit(client, bob, category="meals", amount=900)  # -> rejected (over limit)
    client.post("/expenses", json=PAYLOAD, headers=bob)  # draft, ignored

    review = lambda i, ok: client.post(  # noqa: E731
        f"/expenses/{i}/review", json={"approve": ok, "comment": "x"}, headers=mgr
    )
    assert review(approved, True).status_code == 200
    assert review(paid, True).status_code == 200
    assert review(rejected, False).status_code == 200
    assert client.post(f"/expenses/{paid}/reimburse", headers=adm).status_code == 200

    s = client.get("/expenses/summary", headers=mgr).json()

    assert s["pending_count"] == 1 and s["pending_amount"] == 100
    assert s["awaiting_payment_count"] == 1 and s["awaiting_payment_amount"] == 50
    assert s["reimbursed_count"] == 1 and s["reimbursed_amount"] == 200
    assert s["rejected_count"] == 1
    assert s["flagged_count"] == 1  # the 900 meal is over the 500 limit
    # spend excludes the draft and the rejected expense: 100 + 50 + 200
    assert s["total_requested"] == 350 and s["total_count"] == 3
    assert s["approval_rate"] == 66.7  # 2 approved of 3 decided
    assert s["average_expense"] == round(350 / 3, 2)

    cats = {c["category"]: c for c in s["by_category"]}
    assert cats["travel"]["total"] == 300 and cats["meals"]["total"] == 50
    assert s["by_category"][0]["category"] == "travel"  # sorted by spend

    assert [sp["full_name"] for sp in s["top_spenders"]] == ["Bob", "Alice"]
    assert s["by_month"][-1]["total"] == 350  # everything happened this month
