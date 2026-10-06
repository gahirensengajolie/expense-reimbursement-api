#!/usr/bin/env bash
# Passbook self-check. Run from the project folder:  bash verify.sh
# Starts its own throwaway server + database, so your real data is never touched.
cd "$(dirname "$0")" || exit 1

PORT=8011
B=http://127.0.0.1:$PORT
DB=/tmp/passbook_verify.db
export PYTHONPATH=.
pass=0; fail=0

check() { # name  wanted  got
  if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1))
  else echo "  FAIL  $1 (wanted $2, got $3)"; fail=$((fail+1)); fi
}
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
json() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)" 2>/dev/null; }

rm -f "$DB"

echo "1) Production safety lock"
ENVIRONMENT=production SECRET_KEY=short timeout 10 \
  python3 -m uvicorn app.main:app --port $PORT >/tmp/pv_weak.log 2>&1
rc=$?
[ $rc -ne 124 ] && [ $rc -ne 0 ] && got=refused || got=started
check "weak SECRET_KEY is refused in production" refused "$got"

echo "2) Starting a temporary server"
DATABASE_URL=sqlite:///$DB python3 -m uvicorn app.main:app --port $PORT >/tmp/pv_server.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null; rm -f "$DB"' EXIT
for _ in $(seq 1 40); do curl -s $B/health >/dev/null && break; sleep 0.5; done
check "health endpoint" 200 "$(code $B/health)"
check "frontend page is served" 200 "$(code $B/)"
curl -s $B/ | grep -q "Passbook" && got=yes || got=no
check "frontend page says Passbook" yes "$got"

echo "3) Creating employee, manager, admin"
for u in emp mgr adm; do
  curl -s -o /dev/null -X POST $B/auth/register -H 'content-type: application/json' \
    -d "{\"email\":\"$u@x.com\",\"password\":\"Password123\",\"full_name\":\"User $u\"}"
done
DATABASE_URL=sqlite:///$DB python3 scripts/set_role.py mgr@x.com manager >/dev/null
DATABASE_URL=sqlite:///$DB python3 scripts/set_role.py adm@x.com admin >/dev/null
tok() { curl -s -X POST $B/auth/login -H 'content-type: application/json' \
  -d "{\"email\":\"$1@x.com\",\"password\":\"${2:-Password123}\"}" | json "['access_token']"; }
E=$(tok emp); M=$(tok mgr); A=$(tok adm)
[ -n "$E" ] && [ -n "$M" ] && [ -n "$A" ] && got=ok || got=failed
check "all three can sign in" ok "$got"

echo "4) Role rules"
H='content-type: application/json'
BODY='{"category":"meals","amount":40,"description":"lunch"}'
check "employee creates expense"        201 "$(code -X POST $B/expenses -H "Authorization: Bearer $E" -H "$H" -d "$BODY")"
check "manager cannot create expense"   403 "$(code -X POST $B/expenses -H "Authorization: Bearer $M" -H "$H" -d "$BODY")"
check "admin cannot create expense"     403 "$(code -X POST $B/expenses -H "Authorization: Bearer $A" -H "$H" -d "$BODY")"
check "employee cannot see dashboard"   403 "$(code $B/expenses/summary -H "Authorization: Bearer $E")"
check "manager sees dashboard"          200 "$(code $B/expenses/summary -H "Authorization: Bearer $M")"
check "admin sees dashboard"            200 "$(code $B/expenses/summary -H "Authorization: Bearer $A")"
check "dashboard needs sign-in"         401 "$(code $B/expenses/summary)"
check "employee cannot open admin list" 403 "$(code $B/admin/users -H "Authorization: Bearer $E")"
check "admin opens people list"         200 "$(code $B/admin/users -H "Authorization: Bearer $A")"

echo "5) Full workflow: submit -> approve -> reimburse"
ID=$(curl -s -X GET "$B/expenses" -H "Authorization: Bearer $E" | json "[0]['id']")
check "employee submits"                200 "$(code -X POST $B/expenses/$ID/submit -H "Authorization: Bearer $E")"
check "employee cannot approve"         403 "$(code -X POST $B/expenses/$ID/review -H "Authorization: Bearer $E" -H "$H" -d '{"approve":true,"comment":"x"}')"
check "manager approves"                200 "$(code -X POST $B/expenses/$ID/review -H "Authorization: Bearer $M" -H "$H" -d '{"approve":true,"comment":"ok"}')"
check "manager cannot reimburse"        403 "$(code -X POST $B/expenses/$ID/reimburse -H "Authorization: Bearer $M")"
check "admin reimburses"                200 "$(code -X POST $B/expenses/$ID/reimburse -H "Authorization: Bearer $A")"
check "dashboard counts 1 reimbursed"     1 "$(curl -s $B/expenses/summary -H "Authorization: Bearer $M" | json "['reimbursed_count']")"

echo "6) Company mode: closed sign-up, first admin from environment, teams"
kill $PID 2>/dev/null; wait $PID 2>/dev/null; rm -f "$DB"
ALLOW_SELF_REGISTRATION=false FIRST_ADMIN_EMAIL=root@x.com FIRST_ADMIN_PASSWORD=Root-Passw0rd \
  DATABASE_URL=sqlite:///$DB python3 -m uvicorn app.main:app --port $PORT >/tmp/pv_server2.log 2>&1 &
PID=$!
for _ in $(seq 1 40); do curl -s $B/health >/dev/null && break; sleep 0.5; done
check "sign-up is closed" 403 "$(code -X POST $B/auth/register -H "$H" -d '{"email":"z@x.com","password":"Password123","full_name":"Z"}')"
R=$(tok root Root-Passw0rd)
[ -n "$R" ] && got=ok || got=failed
check "first admin signs in" ok "$got"
check "first admin must change password" True "$(curl -s $B/auth/me -H "Authorization: Bearer $R" | json "['must_change_password']")"
mk() { curl -s -X POST $B/admin/users -H "Authorization: Bearer $R" -H "$H" -d "$1" | json "['id']"; }
M1=$(mk '{"email":"m1@x.com","full_name":"M One","role":"manager","password":"Temp-Passw0rd"}')
M2=$(mk '{"email":"m2@x.com","full_name":"M Two","role":"manager","password":"Temp-Passw0rd"}')
mk "{\"email\":\"e1@x.com\",\"full_name\":\"E One\",\"manager_id\":$M1,\"password\":\"Temp-Passw0rd\"}" >/dev/null
mk "{\"email\":\"e2@x.com\",\"full_name\":\"E Two\",\"manager_id\":$M2,\"password\":\"Temp-Passw0rd\"}" >/dev/null
for e in e1 e2; do
  T=$(tok $e Temp-Passw0rd)
  X=$(curl -s -X POST $B/expenses -H "Authorization: Bearer $T" -H "$H" -d "$BODY" | json "['id']")
  curl -s -o /dev/null -X POST $B/expenses/$X/submit -H "Authorization: Bearer $T"
  eval "X_$e=$X"
done
T1=$(tok m1 Temp-Passw0rd)
check "manager sees only their team (1 expense)" 1 "$(curl -s $B/expenses -H "Authorization: Bearer $T1" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")"
check "manager cannot open another team's expense" 404 "$(code $B/expenses/$X_e2 -H "Authorization: Bearer $T1")"
check "manager approves own team's expense" 200 "$(code -X POST $B/expenses/$X_e1/review -H "Authorization: Bearer $T1" -H "$H" -d '{"approve":true,"comment":"ok"}')"
check "manager dashboard counts team only" 1 "$(curl -s $B/expenses/summary -H "Authorization: Bearer $T1" | json "['total_count']")"
check "admin dashboard counts everyone" 2 "$(curl -s $B/expenses/summary -H "Authorization: Bearer $R" | json "['total_count']")"

echo
if [ $fail -eq 0 ]; then echo "ALL $pass CHECKS PASSED"; else echo "$fail FAILED, $pass passed. Server log: /tmp/pv_server.log"; fi
[ $fail -eq 0 ]
