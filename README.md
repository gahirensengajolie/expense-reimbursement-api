Expense & Reimbursement API
A full-stack expense management system: a FastAPI backend for submitting and
approving employee expenses, plus a React (Vite) frontend — built to
demonstrate real-world backend engineering, QA, and application security
practices. Created as a backend-engineering portfolio project.

Stack
React + Vite — frontend (JSX, dev server proxies API requests to the backend)
FastAPI — web framework
SQLAlchemy — ORM (SQLite by default, swap DATABASE_URL for Postgres)
JWT (python-jose) — access + refresh token auth
passlib/bcrypt — password hashing
pytest — testing
bandit / pip-audit — security scanning
GitHub Actions — CI
Features
Expense lifecycle as a strict state machine: draft → submitted → approved/rejected → reimbursed
Role-based access control (employee / manager / admin) with ownership isolation
Spending policies that flag expenses over category limits, with an audit event
Full audit trail of every expense state change (actor, timestamp, transition)
JWT auth with short-lived access tokens and refresh tokens
React frontend (Orbit) that exercises the real API endpoints
CI pipeline: pytest with an 80% coverage gate, bandit security scan, pip-audit
Quick start
git clone https://github.com/gahirensengajolie/expense-reimbursement-api.git
cd expense-reimbursement-api
python3 -m pip install --user -r requirements.txt
cp .env.example .env
python3 -m uvicorn app.main:app --reload
Visit http://127.0.0.1:8000 for the Orbit frontend or
http://127.0.0.1:8000/docs for interactive Swagger docs.

The --user install above requires no sudo and no virtual environment.
If Ubuntu reports the environment is externally managed, add
--break-system-packages to the install command (keep --user):

python3 -m pip install --user --break-system-packages -r requirements.txt
Virtual-environment setup (alternative)
git clone https://github.com/gahirensengajolie/expense-reimbursement-api.git
cd expense-reimbursement-api
# Ubuntu/Debian only: install the venv module if `python3 -m venv` fails.
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn app.main:app --reload
If the virtual environment was attempted before installing python3-venv,
remove the incomplete environment and recreate it:

rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
React frontend development
The frontend is built with React, JSX, and Vite. Run the backend in one
terminal, then start the Vite dev server in a second terminal:

npm run install:frontend
npm run dev
Run those commands from the project root. Open http://127.0.0.1:5173. Vite
proxies /api/* requests to the FastAPI server on port 8000, so the React UI
exercises the real backend endpoints. If port 8000 is busy, run FastAPI on
another port and point Vite to it:

python3 -m uvicorn app.main:app --reload --port 8001
VITE_API_TARGET=http://127.0.0.1:8001 npm run frontend:dev
To create a production frontend build served by FastAPI:

npm run install:frontend
npm run build
python3 -m uvicorn app.main:app --reload
The production build is written to frontend/dist/ and served from
http://127.0.0.1:8000.

Port already in use
If Uvicorn reports ERROR: [Errno 98] Address already in use, another copy of
the API is already running on port 8000. Open the existing server at
http://127.0.0.1:8000, or start a second copy on another port with
--port 8001. Use Ctrl+C in the terminal running the old server to stop it
before starting the default port again.

Test the approval workflow locally
New registrations intentionally start as employee accounts. This prevents a
public signup from granting itself approval or admin permissions. To exercise
the full workflow locally, create two accounts in Orbit: one employee who
submits an expense and one reviewer account. Promote the reviewer with the
development helper:

python3 scripts/set_role.py reviewer@example.com manager
Then use the following flow:

Sign in as the employee and create an expense draft.
Open its detail view and choose Submit for review.
Sign out and sign in as the manager.
Open Approval queue in the left navigation.
Approve or reject the expense. Rejections require a reason.
If approved, promote an account to admin to test Mark reimbursed and
the People & permissions panel:
python3 scripts/set_role.py admin@example.com admin
The approval queue, audit timeline, policy flags, reimbursement transition,
and role management are all connected to the existing FastAPI endpoints.

Running tests
pytest
pytest --cov=app --cov-report=term-missing
bandit -r app
pip-audit -r requirements.txt
API endpoints
The API supports authenticated expense CRUD operations with ownership
isolation, status filtering, limit/offset pagination, and role-based review
permissions. Draft expenses can be edited or deleted by their owner. Once an
expense is submitted, it remains in the audit trail and can only move through
the workflow.

Method	Endpoint	Purpose
POST	/expenses	Create a draft expense
GET	/expenses	List visible expenses with status, limit, and offset filters
GET	/expenses/{id}	Read one accessible expense
PATCH	/expenses/{id}	Update an owned draft
DELETE	/expenses/{id}	Delete an owned draft
POST	/expenses/{id}/submit	Submit an expense for review
POST	/expenses/{id}/review	Manager/admin approval or rejection
POST	/expenses/{id}/resubmit	Resubmit a rejected expense
POST	/expenses/{id}/reimburse	Admin-only reimbursement
GET	/expenses/{id}/audit	View the expense lifecycle audit trail
The startup path no longer requires slowapi to be installed. Login attempts
are throttled per client and email in the current single-process deployment;
production multi-worker deployments should move the counter to Redis.

Spending policies
Each expense is evaluated against a category policy when it is created. The
current defaults are travel 5000, meals 500, accommodation 3000,
equipment 10000, training 2500, and other categories 1000. Amounts over
the applicable limit are returned with policy_flagged: true, the applicable
policy_limit, and a human-readable policy_flag_reason. A policy_flagged
audit event is also recorded so managers can see why additional review was
triggered. The policy evaluation is computed from the current category and
amount, so changing policy code does not require a destructive database
migration.

Architecture
router  →  service  →  repository  →  database
app/repositories/ — pure SQLAlchemy queries only, no business rules
(e.g. ExpenseRepository.get_by_id, .list, .delete). If you swapped
the database, this is the only layer that would need to change.
app/services/ — all business logic and authorization rules live
here (ownership checks, state-machine transitions, the self-approval
block). Services raise plain Python exceptions from app/exceptions.py
and have zero dependency on FastAPI, so they can be unit-tested
directly (see tests/test_expense_service_unit.py) without spinning up
the web layer at all.
app/routers/ — thin controllers: parse the request, call a
service, return the result. A single set of exception handlers in
app/main.py maps domain exceptions (NotFoundError, ForbiddenError,
ConflictError, BadRequestError, AuthenticationError) to the right
HTTP status codes, so routers never contain try/except blocks.
Domain model
Users have a role: employee, manager, or admin.
Expenses move through a state machine:
draft → submitted → approved/rejected → reimbursed
(rejected can be resubmitted: rejected → draft)
Every state change is written to an audit log (who did what, when).
Roles & permissions
Action	Employee	Manager	Admin
Create/edit own draft	✅	✅	✅
Delete own draft	✅	✅	✅
Submit own expense	✅	✅	✅
View own expenses	✅	✅	✅
View all expenses	❌	✅	✅
Approve/reject (not own)	❌	✅	✅
Reimburse	❌	❌	✅
Manage user roles	❌	❌	✅
Note on delete: DELETE /expenses/{id} only works on draft
expenses. Once submitted, an expense enters the approval/audit trail and
must be tracked (approved, rejected, or resubmitted) — never silently
removed. This is a deliberate business rule, not a missing feature.

QA approach
Unit-level state machine tests — every illegal transition
(e.g. approving an already-approved expense) is tested and rejected.
Authorization matrix (tests/test_authorization.py) — the core of
the QA suite. Explicitly tries to break access control: one employee
reading another’s data, a manager self-approving, an employee calling
admin-only endpoints, etc.
Input validation edge cases — negative/zero/oversized amounts,
oversized strings, missing fields.
Coverage gate in CI — build fails if coverage drops below 80%.
Run pytest -v to see the full list of test names/intentions — the test
names describe the security property or business rule under test.

Security write-up
Threats considered and how they’re mitigated, loosely mapped to OWASP
Top 10 categories:

A01 – Broken Access Control
Every expense lookup goes through a single _get_owned_or_403 helper so
authorization logic isn’t duplicated (and forgotten) across handlers.
Non-owned, non-privileged access returns 404 rather than 403 to avoid
confirming a resource’s existence. A manager is explicitly blocked from
approving their own submitted expense — role-gating the endpoint alone
isn’t enough to prevent that self-approval loophole.

A02 – Cryptographic Failures
Passwords are hashed with bcrypt (adaptive cost factor) — never stored or
logged in plaintext. JWT secret key is read from environment/.env, never
hardcoded, and access tokens are short-lived (15 min) with separate
longer-lived refresh tokens.

A03 – Injection
All queries go through SQLAlchemy’s ORM/parameterized queries — no raw SQL
string interpolation anywhere in the codebase.

A04 – Insecure Design
The expense status field is a strict state machine (ALLOWED_TRANSITIONS)
rather than a free-form string, so the API can’t be coerced into an
invalid state (e.g. draft → reimbursed directly).

A05 – Security Misconfiguration
Security headers (X-Content-Type-Options, X-Frame-Options,
Referrer-Policy) are added to every response. .env is git-ignored;
.env.example documents required variables without real values.

A07 – Identification and Authentication Failures
Login is rate-limited (5 attempts per 60 seconds, keyed by client host +
email) via a dependency-free in-memory limiter — see _enforce_login_limit
in app/routers/auth.py. Login failure messages are identical whether the
email exists or not, to avoid user enumeration. Note: the in-memory counter
is per-process, so a multi-worker production deployment should move it to
a shared store (e.g. Redis) to stay effective across workers.

A09 – Security Logging and Monitoring Failures
Every expense state change is recorded in an audit_logs table (actor,
timestamp, from/to status, comment) — supports after-the-fact
investigation of disputed approvals.

Known limitations / next steps
Single-tenant only (no multi-company isolation) — kept out of scope to
ship a working v1 fast; would be the natural next feature.
No file/receipt upload yet.
No account lockout after N failed logins (only rate limiting).
pip-audit runs in CI but doesn’t block merges yet — findings are
reviewed manually.
The login rate limiter is in-memory and per-process; fine for a single
deployment/demo, but would need a shared store (Redis) behind a
multi-worker production deployment.
