// What a manager sees and can do, including team boundaries.
const run = Date.now().toString(36)

describe('Manager', () => {
  let m1 // our manager
  let m2 // another team's manager
  let e1 // reports to m1
  let e2 // reports to m2
  let teamExpense
  let otherTeamExpense
  const teamText = `Team expense ${run}`
  const otherText = `Other team expense ${run}`

  before(() => {
    const seed = (name, slug, extra = {}) =>
      cy.task('seedUser', { full_name: `${name} ${run}`, email: `${slug}-${run}@example.com`, ...extra })

    seed('Max Manager', 'max', { role: 'manager' })
      .then((user) => {
        m1 = user
        return seed('Moe Manager', 'moe', { role: 'manager' })
      })
      .then((user) => {
        m2 = user
        return seed('Ed Employee', 'ed', { manager_id: m1.id })
      })
      .then((user) => {
        e1 = user
        return seed('Ann Employee', 'ann', { manager_id: m2.id })
      })
      .then((user) => {
        e2 = user
        return cy.fileExpense(e1, { description: teamText, amount: 80 })
      })
      .then((expense) => {
        teamExpense = expense
        return cy.fileExpense(e2, { description: otherText, amount: 60 })
      })
      .then((expense) => {
        otherTeamExpense = expense
      })
  })

  it('gets the manager navigation and cannot file expenses', () => {
    cy.openApp(m1, '/')

    cy.location('hash').should('eq', '#/dashboard')
    cy.get('.role-badge').should('have.text', 'Manager')
    cy.get('nav').within(() => {
      cy.contains('a', 'Spending dashboard').should('be.visible')
      cy.contains('a', 'Approval queue').should('be.visible')
      cy.contains('a', 'All expenses').should('be.visible')
      cy.contains('a', 'My expenses').should('not.exist')
      cy.contains('a', 'Payments').should('not.exist')
      cy.contains('a', 'People & roles').should('not.exist')
    })
    cy.contains('button', 'New expense').should('not.exist')
  })

  it('shows a spending dashboard for their own team only', () => {
    cy.openApp(m1, '/dashboard')

    cy.contains('h1', 'Spending dashboard').should('be.visible')
    ;['Total spend', 'Awaiting review', 'Approved, unpaid', 'Reimbursed', 'Approval rate', 'Average expense', 'Policy flags'].forEach(
      (label) => cy.contains('.metric-label', label).should('be.visible')
    )
    ;['Spend by month', 'Where the money goes', 'Approval pipeline', 'Top spenders'].forEach((title) =>
      cy.contains('.section-heading', title).should('be.visible')
    )
    cy.contains('.card', 'Top spenders').should('contain', e1.full_name).and('not.contain', e2.full_name)
  })

  it("lists only their team's submitted expenses in the approval queue", () => {
    cy.openApp(m1, '/queue')

    cy.contains('.queue-row', teamText).should('contain', e1.full_name)
    cy.contains('.queue-row', otherText).should('not.exist')
  })

  it('approves an expense from the queue', () => {
    const description = `To approve ${run}`
    cy.fileExpense(e1, { description })
    cy.openApp(m1, '/queue')

    cy.answerPromptWith('Approved in the e2e test')
    cy.contains('.queue-row', description).contains('button', 'Approve').click()
    cy.get('.toast').should('contain', 'Expense approved.')
    cy.contains('.queue-row', description).should('not.exist')
  })

  it('refuses to reject without a reason, then rejects with one', () => {
    const description = `To reject ${run}`
    cy.fileExpense(e1, { description })
    cy.openApp(m1, '/queue')

    cy.answerPromptWith('', 'Missing receipt')
    cy.contains('.queue-row', description).contains('button', 'Reject').click()
    cy.get('.toast').should('contain', 'Add a reason before rejecting an expense.')
    cy.contains('.queue-row', description).should('exist')

    cy.contains('.queue-row', description).contains('button', 'Reject').click()
    cy.get('.toast').should('contain', 'Expense rejected.')
    cy.contains('.queue-row', description).should('not.exist')
  })

  it("cannot open another team's expense or file expenses through the API", () => {
    cy.apiAs(m1, 'GET', `/expenses/${otherTeamExpense.id}`).its('status').should('eq', 404)
    cy.apiAs(m1, 'POST', `/expenses/${otherTeamExpense.id}/review`, { approve: true, comment: 'x' })
      .its('status')
      .should('eq', 404)
    cy.apiAs(m1, 'GET', `/expenses/${teamExpense.id}`).its('status').should('eq', 200)
    cy.apiAs(m1, 'POST', '/expenses', { category: 'meals', amount: 10, description: 'x' })
      .its('status')
      .should('eq', 403)
  })

  it('lists all of their team\'s expenses with who filed them', () => {
    cy.openApp(m1, '/expenses')

    cy.contains('h1', 'All expenses').should('be.visible')
    cy.contains('tr', teamText).should('contain', e1.full_name)
    cy.contains('tr', otherText).should('not.exist')
  })

  it("exports a CSV of their team's expenses", () => {
    cy.openApp(m1, '/expenses')
    cy.contains('tr', teamText).should('be.visible') // list has loaded

    cy.contains('button', 'Export CSV').click()
    cy.get('.toast').should('contain', 'CSV exported.')
    cy.readFile(`${Cypress.config('downloadsFolder')}/passbook-expenses.csv`, { timeout: 10000 })
      .should('contain', 'id,submitted_by,category,amount,status')
      .and('contain', teamText)
      .and('not.contain', otherText)
  })

  it('is sent to their dashboard when opening admin-only pages', () => {
    cy.openApp(m1, '/payments')
    cy.location('hash').should('eq', '#/dashboard')

    cy.visit('/#/people')
    cy.location('hash').should('eq', '#/dashboard')
  })
})
