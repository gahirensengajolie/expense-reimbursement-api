# Cypress end-to-end tests: how to add them

    cd ~/projects/expense-api
    git add -A && git commit -m "Snapshot before e2e tests"      # ok if "nothing to commit"
    git branch backup-before-e2e

    cp -r ~/Downloads/expense-api-cypress/. .
    chmod +x scripts/e2e.sh

    # 1) backend tests still pass (want: 110 passed)
    python3 -m pytest -q --cov=app --cov-fail-under=80

    # 2) install Cypress (downloads ~200 MB the first time) and run the end-to-end tests
    cd frontend
    npm ci
    npm run e2e              # headless. Or: npm run e2e:open  to watch it in a browser window

See frontend/cypress/README.md for what is covered and how to debug a failing test.
To undo: git checkout backup-before-e2e
