#!/usr/bin/env bash
# Run the Cypress end-to-end tests against a throwaway copy of the real app.
#
#   bash scripts/e2e.sh          headless, like CI   (or: cd frontend && npm run e2e)
#   bash scripts/e2e.sh open     interactive Cypress window  (npm run e2e:open)
#
# It builds the frontend, starts the API (serving that build) on a temporary
# SQLite database in "company mode" (sign-up closed, first admin from the
# environment), runs Cypress, then stops the server and deletes the database.
# Your real .env and database are never touched.
set -u
cd "$(dirname "$0")/.." || exit 1

PORT="${E2E_PORT:-8010}"
DB="$(mktemp -u /tmp/passbook_e2e_XXXXXX).db"
LOG="${TMPDIR:-/tmp}/passbook_e2e_server.log"
export CYPRESS_BASE_URL="http://127.0.0.1:${PORT}"

echo "==> Building the frontend"
(cd frontend && npm run build >/dev/null) || { echo "Frontend build failed"; exit 1; }

echo "==> Starting the app on ${CYPRESS_BASE_URL} (temporary database)"
ENVIRONMENT=development \
SECRET_KEY=e2e-only-secret-key-never-use-in-production-0123456789 \
DATABASE_URL="sqlite:///${DB}" \
ALLOW_SELF_REGISTRATION=false \
FIRST_ADMIN_EMAIL=e2e-admin@example.com \
FIRST_ADMIN_PASSWORD=E2e-Initial-Pass1 \
LOGIN_MAX_ATTEMPTS=1000 \
LOG_LEVEL=WARNING \
python3 -m uvicorn app.main:app --port "$PORT" >"$LOG" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null; rm -f "$DB"' EXIT

for _ in $(seq 1 60); do
  curl -fs "${CYPRESS_BASE_URL}/health" >/dev/null 2>&1 && break
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "The app stopped during startup:"; tail -20 "$LOG"; exit 1; }
  sleep 0.5
done
curl -fs "${CYPRESS_BASE_URL}/health" >/dev/null 2>&1 || { echo "The app did not become ready:"; tail -20 "$LOG"; exit 1; }

echo "==> Running Cypress"
cd frontend || exit 1
if [ -n "${E2E_RUNNER:-}" ]; then
  eval "$E2E_RUNNER"            # advanced: replace Cypress with another command
elif [ "${1:-run}" = "open" ]; then
  npx cypress open --e2e
else
  npx cypress run
fi
