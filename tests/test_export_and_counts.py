import csv
import io

from tests.conftest import make_admin, make_manager, register_and_login

PAYLOAD = {"category": "travel", "amount": 100.0, "description": "trip"}


def _employee(client, email="emp@example.com"):
    return register_and_login(client, email, full_name="Emp")


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


def _rows(response):
    return list(csv.DictReader(io.StringIO(response.text)))


def test_export_and_counts_are_for_reviewers_only(client):
    headers = _employee(client)
    assert client.get("/expenses/export", headers=headers).status_code == 403
    assert client.get("/expenses/counts", headers=headers).status_code == 403


def test_export_has_submitted_expenses_but_no_drafts(client, db_session):
    emp = _employee(client)
    _submit(client, emp, description="Taxi")
    client.post("/expenses", json=PAYLOAD, headers=emp)  # stays a private draft
    response = client.get("/expenses/export", headers=_admin(client, db_session))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = _rows(response)
    assert len(rows) == 1 and rows[0]["description"] == "Taxi" and rows[0]["status"] == "submitted"


def test_export_neutralises_spreadsheet_formulas(client, db_session):
    _submit(client, _employee(client), description='=HYPERLINK("http://evil.example")')
    rows = _rows(client.get("/expenses/export", headers=_admin(client, db_session)))
    assert rows[0]["description"].startswith("'=")


def test_export_status_filter_and_counts(client, db_session):
    emp = _employee(client)
    first, _second = _submit(client, emp), _submit(client, emp)
    admin = _admin(client, db_session)
    assert client.get("/expenses/counts", headers=admin).json() == {"pending": 2, "payable": 0}

    review = client.post(f"/expenses/{first}/review", json={"approve": True, "comment": "ok"}, headers=admin)
    assert review.status_code == 200
    assert client.get("/expenses/counts", headers=admin).json() == {"pending": 1, "payable": 1}
    approved = _rows(client.get("/expenses/export?status=approved", headers=admin))
    assert [r["status"] for r in approved] == ["approved"]


def test_manager_counts_cover_unassigned_employees(client, db_session):
    _submit(client, _employee(client))
    register_and_login(client, "mgr@example.com", full_name="Mgr")
    make_manager(db_session, "mgr@example.com")
    headers = register_and_login(client, "mgr@example.com", full_name="Mgr")
    assert client.get("/expenses/counts", headers=headers).json()["pending"] == 1
