# Phase 1 upgrade: company-ready accounts, teams, passwords

Includes everything from the earlier CI fix, so you can apply this on top of it.

    cd ~/projects/expense-api
    git add -A && git commit -m "Snapshot before phase 1"   # ok if "nothing to commit"
    git branch backup-before-phase1                          # safety copy

    rm -f expense.db test.db        # database layout changed; this is local dev data only
    rm -rf frontend/dist            # old build files
    cp -r ~/Downloads/expense-api-phase1/. .

    python3 -m pytest -q --cov=app --cov-fail-under=80      # want: 101 passed
    bash verify.sh                                          # want: ALL 28 CHECKS PASSED

Try it in the browser in "company mode":

    ALLOW_SELF_REGISTRATION=false FIRST_ADMIN_EMAIL=admin@test.com \
    FIRST_ADMIN_PASSWORD=Temp-Passw0rd python3 -m uvicorn app.main:app --port 8000

Open http://127.0.0.1:8000 and sign in as admin@test.com / Temp-Passw0rd. You will be asked to choose a
new password. Then People -> Add person: create two managers and a few employees, assign employees
to managers, and sign in as each to compare what they see.

Then: git add -A && git commit -m "Add accounts, teams, passwords" && git push
To undo everything: git checkout backup-before-phase1
