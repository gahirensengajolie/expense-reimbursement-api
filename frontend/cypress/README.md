# End-to-end tests (Cypress)

These tests open a real browser, sign in as an employee, a manager and an admin, and use the
app the way a person would. They run against a **temporary copy** of the app and database,
so your real data is never touched.

## Run them

    cd frontend
    npm ci                 # first time only (downloads Cypress, ~200 MB)
    npm run e2e            # headless: prints a pass/fail list, like CI
    npm run e2e:open       # interactive window: watch each step, great for debugging

`npm run e2e` calls `scripts/e2e.sh`, which builds the frontend, starts the app on port 8010
(sign-up closed, first admin from the environment), runs Cypress, then cleans up.
If port 8010 is busy: `E2E_PORT=8011 npm run e2e`.

## What is covered (35 tests)

| File | Covers |
|---|---|
| `auth.cy.js` | sign in/out, wrong password, closed sign-up, forced password change, disabled account |
| `employee.cy.js` | employee-only navigation, create / submit / delete drafts, over-limit flag, rejected -> resubmit, privacy, API refusals |
| `manager.cy.js` | manager navigation, no "New expense", team-only dashboard and queue, approve / reject, other teams blocked, CSV export |
| `admin.cy.js` | admin navigation, payments, add person, assign manager, disable / enable, reset password, self-protection |
| `workflow.cy.js` | one expense from draft to reimbursed across all three roles, and reject -> resubmit |
| `responsive.cy.js` | navigation and sign-in on a phone-sized screen |

## How the tests are built

- **Arrange through the API, act through the screen.** `cypress/support/tasks.js` creates people and
  expenses directly (fast, reliable); the test then uses the real buttons and checks what appears.
- **Every run uses unique names** (a short `run` id), so tests never collide in the shared test database.
- Handy commands live in `cypress/support/commands.js`: `cy.field('Work email')` (find an input by its
  label), `cy.openApp(user, '/queue')`, `cy.fileExpense(user, {...})`, `cy.decideExpense(...)`,
  `cy.answerPromptWith('comment')` (the approval queue uses a browser prompt).

## When a test fails

1. Run `npm run e2e:open` and click the failing test: you can step through it.
2. After a headless run, look in `cypress/screenshots/` for a picture of the failure
   (CI uploads them as a downloadable artifact).
3. The app log of the last run is at `/tmp/passbook_e2e_server.log`.
4. If you changed button text or labels in the app, update the matching text in the tests.

## "npm ci" fails at "Downloading Cypress"

Cypress downloads its own ~200 MB test browser when you install. On a slow or interrupted
connection that download fails. Nothing is wrong with the project. To recover:

    cd frontend
    CYPRESS_INSTALL_BINARY=0 npm ci        # installs everything except the Cypress browser (the app works)
    df -h ~ | tail -1                      # need roughly 1 GB free
    DEBUG=cypress:cli* npx cypress install # install just the browser, with detailed messages

If that keeps failing, download it yourself with a command that can resume, then install from the file:

    curl -L -C - -o ~/Downloads/cypress-linux-x64.zip "https://download.cypress.io/desktop/16.1.1?platform=linux&arch=x64"
    # if it stops, run the same command again: it continues where it left off
    CYPRESS_INSTALL_BINARY="$HOME/Downloads/cypress-linux-x64.zip" npx cypress install
    npx cypress verify

If `cypress verify` mentions missing libraries (Ubuntu), install them:

    sudo apt-get install -y libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libnss3 libxss1 libasound2 libxtst6 xauth xvfb
