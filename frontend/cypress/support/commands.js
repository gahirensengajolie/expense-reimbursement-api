const escapeRegExp = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// Find a form control by its exact visible label:  cy.field('Work email').type('a@b.com')
Cypress.Commands.add('field', (label) =>
  cy
    .contains('label > span', new RegExp(`^${escapeRegExp(label)}$`))
    .parent()
    .find('input, select, textarea')
)

// Sign in by typing into the real login form.
Cypress.Commands.add('signInThroughForm', (email, password) => {
  cy.visit('/')
  cy.field('Work email').type(email)
  cy.field('Password').type(password, { log: false })
  cy.contains('button', 'Sign in').click()
})

// Fast sign-in without the form (API login, cached per test file), for tests
// that are about something other than signing in.
Cypress.Commands.add('loginAs', (user) => {
  cy.session(user.email, () => {
    cy.request('POST', '/auth/login', { email: user.email, password: user.password }).then(({ body }) => {
      window.localStorage.setItem('passbook_access', body.access_token)
      window.localStorage.setItem('passbook_refresh', body.refresh_token)
    })
  })
})

// Sign in as `user` and open the app at a route, e.g. cy.openApp(manager, '/queue').
// Always loads the page fresh, so data arranged earlier through the API is shown.
Cypress.Commands.add('openApp', (user, route = '/') => {
  cy.loginAs(user)
  cy.visit(`/#${route}`)
})

// Call the API as a user (or 'admin'); yields { status, data }.
Cypress.Commands.add('apiAs', (user, method, path, body) => cy.task('api', { method, path, as: user, body }))

// An employee files an expense through the API; submitted by default. Yields the expense.
Cypress.Commands.add('fileExpense', (user, { category = 'meals', amount = 25, description, submit = true }) =>
  cy.apiAs(user, 'POST', '/expenses', { category, amount, description }).then((created) => {
    expect(created.status, 'expense created').to.eq(201)
    if (!submit) return created.data
    return cy.apiAs(user, 'POST', `/expenses/${created.data.id}/submit`).then((submitted) => {
      expect(submitted.status, 'expense submitted').to.eq(200)
      return submitted.data
    })
  })
)

// A manager/admin decides on an expense through the API.
Cypress.Commands.add('decideExpense', (reviewer, expenseId, approve, comment = 'ok') =>
  cy.apiAs(reviewer, 'POST', `/expenses/${expenseId}/review`, { approve, comment }).then((result) => {
    expect(result.status, approve ? 'expense approved' : 'expense rejected').to.eq(200)
    return result.data
  })
)

// Answer the browser's window.prompt() used by the approval queue.
Cypress.Commands.add('answerPromptWith', (...answers) => {
  cy.window().then((win) => {
    const prompt = cy.stub(win, 'prompt')
    answers.forEach((answer, index) => prompt.onCall(index).returns(answer))
  })
})
