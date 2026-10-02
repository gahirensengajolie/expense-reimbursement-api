"""
Boundary-value tests.

Where test_expense_workflow.py and test_auth.py check that validation
exists at all (a clearly-too-big amount, a clearly-too-short password),
this file checks the EXACT edges of each rule: the last value that should
pass, and the first value that should fail, on both sides of every limit
in the schemas. This is where off-by-one bugs (> vs >=, and vice versa)
actually get caught.
"""

from app.schemas.expense import MAX_EXPENSE_AMOUNT
from tests.conftest import register_and_login


def create_expense(client, headers, **overrides):
    payload = {"category": "travel", "amount": 10.0, "description": "x"}
    payload.update(overrides)
    return client.post("/expenses", json=payload, headers=headers)


# ---- expense amount: (0, MAX_EXPENSE_AMOUNT] --------------------------


def test_amount_at_max_is_accepted(client):
    headers = register_and_login(client, "bound-amt-max@example.com")
    resp = create_expense(client, headers, amount=MAX_EXPENSE_AMOUNT)
    assert resp.status_code == 201


def test_amount_one_cent_over_max_is_rejected(client):
    headers = register_and_login(client, "bound-amt-over@example.com")
    resp = create_expense(client, headers, amount=MAX_EXPENSE_AMOUNT + 0.01)
    assert resp.status_code == 422


def test_smallest_positive_amount_is_accepted(client):
    headers = register_and_login(client, "bound-amt-min@example.com")
    resp = create_expense(client, headers, amount=0.01)
    assert resp.status_code == 201


def test_amount_exactly_zero_is_rejected(client):
    headers = register_and_login(client, "bound-amt-zero@example.com")
    resp = create_expense(client, headers, amount=0)
    assert resp.status_code == 422


# ---- description length: [0, 1000] -------------------------------------


def test_description_at_max_length_is_accepted(client):
    headers = register_and_login(client, "bound-desc-max@example.com")
    resp = create_expense(client, headers, description="x" * 1000)
    assert resp.status_code == 201


def test_description_one_char_over_max_is_rejected(client):
    headers = register_and_login(client, "bound-desc-over@example.com")
    resp = create_expense(client, headers, description="x" * 1001)
    assert resp.status_code == 422


def test_empty_description_is_accepted(client):
    # description has a default of "" and no min_length, so empty is valid
    headers = register_and_login(client, "bound-desc-empty@example.com")
    resp = create_expense(client, headers, description="")
    assert resp.status_code == 201


# ---- password length: [8, 128] ------------------------------------------


def test_password_at_min_length_is_accepted(client):
    resp = client.post(
        "/auth/register",
        json={"email": "bound-pw-min@example.com", "password": "a" * 8, "full_name": "A"},
    )
    assert resp.status_code == 201


def test_password_one_char_under_min_is_rejected(client):
    resp = client.post(
        "/auth/register",
        json={"email": "bound-pw-under@example.com", "password": "a" * 7, "full_name": "A"},
    )
    assert resp.status_code == 422


def test_password_at_max_length_is_accepted(client):
    resp = client.post(
        "/auth/register",
        json={"email": "bound-pw-max@example.com", "password": "a" * 128, "full_name": "A"},
    )
    assert resp.status_code == 201


def test_password_one_char_over_max_is_rejected(client):
    resp = client.post(
        "/auth/register",
        json={"email": "bound-pw-over@example.com", "password": "a" * 129, "full_name": "A"},
    )
    assert resp.status_code == 422


# ---- pagination: limit in [1, 100], offset >= 0 --------------------------


def test_list_limit_at_max_is_accepted(client):
    headers = register_and_login(client, "bound-limit-max@example.com")
    resp = client.get("/expenses?limit=100", headers=headers)
    assert resp.status_code == 200


def test_list_limit_over_max_is_rejected(client):
    headers = register_and_login(client, "bound-limit-over@example.com")
    resp = client.get("/expenses?limit=101", headers=headers)
    assert resp.status_code == 422


def test_list_limit_at_min_is_accepted(client):
    headers = register_and_login(client, "bound-limit-min@example.com")
    resp = client.get("/expenses?limit=1", headers=headers)
    assert resp.status_code == 200


def test_list_limit_zero_is_rejected(client):
    headers = register_and_login(client, "bound-limit-zero@example.com")
    resp = client.get("/expenses?limit=0", headers=headers)
    assert resp.status_code == 422


def test_list_offset_zero_is_accepted(client):
    headers = register_and_login(client, "bound-offset-zero@example.com")
    resp = client.get("/expenses?offset=0", headers=headers)
    assert resp.status_code == 200


def test_list_offset_negative_is_rejected(client):
    headers = register_and_login(client, "bound-offset-neg@example.com")
    resp = client.get("/expenses?offset=-1", headers=headers)
    assert resp.status_code == 422


# ---- spending policy: flag boundary is strictly > limit, not >= ---------


def test_amount_exactly_at_policy_limit_is_not_flagged(client):
    # meals limit is 500.0; the policy uses `amount > limit`, so exactly
    # 500 must NOT be flagged -- this is the off-by-one case that matters.
    headers = register_and_login(client, "bound-policy-exact@example.com")
    resp = create_expense(client, headers, category="meals", amount=500.0)
    assert resp.status_code == 201
    assert resp.json()["policy_flagged"] is False


def test_amount_one_cent_over_policy_limit_is_flagged(client):
    headers = register_and_login(client, "bound-policy-over@example.com")
    resp = create_expense(client, headers, category="meals", amount=500.01)
    assert resp.status_code == 201
    assert resp.json()["policy_flagged"] is True


# ---- login rate limit: exactly 5 attempts allowed per window ------------


def test_fifth_failed_login_is_still_allowed_sixth_is_blocked(client):
    email = "bound-ratelimit@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "GoodPass123", "full_name": "A"},
    )
    statuses = []
    for _ in range(6):
        resp = client.post("/auth/login", json={"email": email, "password": "wrong"})
        statuses.append(resp.status_code)

    # first 5 attempts are evaluated as real login attempts (401, wrong password)
    assert statuses[:5] == [401, 401, 401, 401, 401]
    # the 6th is blocked by the limiter itself
    assert statuses[5] == 429
