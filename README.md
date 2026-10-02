# Expense & Reimbursement API

A backend API for submitting and approving employee expenses, built to
demonstrate real-world backend engineering, QA, and application security
practices — built as a backend-engineering intern portfolio project.

## Stack

- **FastAPI** — web framework
- **SQLAlchemy** — ORM (SQLite by default, swap `DATABASE_URL` for Postgres)
- **JWT** (python-jose) — access + refresh token auth
- **passlib/bcrypt** — password hashing
- **pytest** — testing
- **bandit / pip-audit** — security scanning
- **GitHub Actions** — CI

## Setup

```bash
git clone <your-repo-url>
cd expense-api
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit SECRET_KEY to a real random value
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive Swagger docs.

## Running tests

```bash
pytest                                   # run all tests
pytest --cov=app --cov-report=term-missing   # with coverage
bandit -r app                            # static security scan
pip-audit -r requirements.txt            # dependency vulnerability scan
```

## Architecture

```
router  →  service  →  repository  →  database
```

- **`app/repositories/`** — pure SQLAlchemy queries only, no business rules
  (e.g. `ExpenseRepository.get_by_id`, `.list`, `.delete`). If you swapped
  the database, this is the only layer that would need to change.
- **`app/services/`** — all business logic and authorization rules live
  here (ownership checks, state-machine transitions, the self-approval
  block). Services raise plain Python exceptions from `app/exceptions.py`
  and have **zero dependency on FastAPI**, so they can be unit-tested
  directly (see `tests/test_expense_service_unit.py`) without spinning up
  the web layer at all.
- **`app/routers/`** — thin controllers: parse the request, call a
  service, return the result. A single set of exception handlers in
  `app/main.py` maps domain exceptions (`NotFoundError`, `ForbiddenError`,
  `ConflictError`, `BadRequestError`, `AuthenticationError`) to the right
  HTTP status codes, so routers never contain `try/except` blocks.

## Domain model

- **Users** have a role: `employee`, `manager`, or `admin`.
- **Expenses** move through a state machine:
  `draft → submitted → approved/rejected → reimbursed`
  (rejected can be resubmitted: `rejected → draft`)
- Every state change is written to an **audit log** (who did what, when).

## Roles & permissions

| Action                     | Employee | Manager | Admin |
|-----------------------------|:--------:|:-------:|:-----:|
| Create/edit own draft       | ✅       | ✅      | ✅    |
| Delete own draft            | ✅       | ✅      | ✅    |
| Submit own expense          | ✅       | ✅      | ✅    |
| View own expenses           | ✅       | ✅      | ✅    |
| View all expenses           | ❌       | ✅      | ✅    |
| Approve/reject (not own)    | ❌       | ✅      | ✅    |
| Reimburse                   | ❌       | ❌      | ✅    |
| Manage user roles           | ❌       | ❌      | ✅    |

**Note on delete:** `DELETE /expenses/{id}` only works on `draft`
expenses. Once submitted, an expense enters the approval/audit trail and
must be tracked (approved, rejected, or resubmitted) — never silently
removed. This is a deliberate business rule, not a missing feature.

## QA approach

- **Unit-level state machine tests** — every illegal transition
  (e.g. approving an already-approved expense) is tested and rejected.
- **Authorization matrix** (`tests/test_authorization.py`) — the core of
  the QA suite. Explicitly tries to break access control: one employee
  reading another's data, a manager self-approving, an employee calling
  admin-only endpoints, etc.
- **Input validation edge cases** — negative/zero/oversized amounts,
  oversized strings, missing fields.
- **Coverage gate in CI** — build fails if coverage drops below 80%.

Run `pytest -v` to see the full list of test names/intentions — the test
names describe the security property or business rule under test.

## Security write-up

Threats considered and how they're mitigated, loosely mapped to OWASP
Top 10 categories:

**A01 – Broken Access Control**
Every expense lookup goes through a single `_get_owned_or_403` helper so
authorization logic isn't duplicated (and forgotten) across handlers.
Non-owned, non-privileged access returns `404` rather than `403` to avoid
confirming a resource's existence. A manager is explicitly blocked from
approving their own submitted expense — role-gating the endpoint alone
isn't enough to prevent that self-approval loophole.

**A02 – Cryptographic Failures**
Passwords are hashed with bcrypt (adaptive cost factor) — never stored or
logged in plaintext. JWT secret key is read from environment/`.env`, never
hardcoded, and access tokens are short-lived (15 min) with separate
longer-lived refresh tokens.

**A03 – Injection**
All queries go through SQLAlchemy's ORM/parameterized queries — no raw SQL
string interpolation anywhere in the codebase.

**A04 – Insecure Design**
The expense status field is a strict state machine (`ALLOWED_TRANSITIONS`)
rather than a free-form string, so the API can't be coerced into an
invalid state (e.g. `draft → reimbursed` directly).

**A05 – Security Misconfiguration**
Security headers (`X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy`) are added to every response. `.env` is git-ignored;
`.env.example` documents required variables without real values.

**A07 – Identification and Authentication Failures**
Login is rate-limited (5/min per IP) to slow brute-force attempts. Login
failure messages are identical whether the email exists or not, to avoid
user enumeration.

**A09 – Security Logging and Monitoring Failures**
Every expense state change is recorded in an `audit_logs` table (actor,
timestamp, from/to status, comment) — supports after-the-fact
investigation of disputed approvals.

## Known limitations / next steps

- Single-tenant only (no multi-company isolation) — kept out of scope to
  ship a working v1 fast; would be the natural next feature.
- No file/receipt upload yet.
- No account lockout after N failed logins (only rate limiting).
- `pip-audit` runs in CI but doesn't block merges yet — findings are
  reviewed manually.
