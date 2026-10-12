// What an employee sees and can do.
const run = Date.now().toString(36)

describe('Employee', () => {
  let manager
  let employee
  let colleague

  before(() => {
    cy.task('seedUser', { full_name: `Mia Manager ${run}`, email: `mia-${run}@example.com`, role: 'manager' })
      .then((user) => {
        manager = user
        return cy.task('seedUser', {
          full_name: `Eve Employee ${run}`,
          email: `eve-${run}@example.com`,
          manager_id: manager.id,
        })
      })
      .then((user) => {
        employee = user
        return cy.task('seedUser', {
          full_name: `Cal Colleague ${run}`,
          email: `cal-${run}@example.com`,
          manager_id: manager.id,
        })
      })
      .then((user) => {
        colleague = user
      })
  })

  it('only gets the employee navigation', () => {
    cy.openApp(employee, '/')

    cy.get('.role-badge').should('have.text', 'Employee')
    cy.get('nav').within(() => {
      cy.contains('a', 'Overview').should('be.visible')
      cy.contains('a', 'My expenses').should('be.visible')
      cy.contains('a', 'Approval queue').should('not.exist')
      cy.contains('a', 'Spending dashboard').should('not.exist')
      cy.contains('a', 'Payments').should('not.exist')
      cy.contains('a', 'People & roles').should('not.exist')
    })
  })

  it('is sent back to their own home when opening a manager-only page', () => {
    cy.openApp(employee, '/dashboard')

    cy.location('hash').should('eq', '#/overview')
    cy.contains('h1', 'Spending dashboard').should('not.exist')
  })

  it('creates a draft and submits it for review', () => {
    const description = `Client lunch ${run}`
    cy.openApp(employee, '/overview')

    cy.contains('button', 'New expense').click()
    cy.contains('.modal-head h2', 'New expense').should('be.visible')
    cy.field('Category').select('meals')
    cy.field('Amount (USD)').type('42.50')
    cy.field('What was this for?').type(description)
    cy.contains('button', 'Create draft').click()
    cy.get('.toast').should('contain', 'Draft created.')

    cy.contains('nav a', 'My expenses').click()
    cy.contains('tr', description).should('contain', '$42.50').and('contain', 'draft').click()
    cy.contains('.modal-head h2', 'Expense #').should('be.visible')
    cy.contains('button', 'Submit for review').click()

    cy.get('.toast').should('contain', 'Expense updated.')
    cy.contains('tr', description).should('contain', 'submitted')
  })

  it('flags an expense that is over the category limit', () => {
    const description = `Gala dinner ${run}`
    cy.fileExpense(employee, { category: 'meals', amount: 900, description, submit: false })
    cy.openApp(employee, '/expenses')

    cy.contains('tr', description).should('contain', 'over limit')
  })

  it('deletes a draft', () => {
    const description = `Mistaken draft ${run}`
    cy.fileExpense(employee, { description, submit: false })
    cy.openApp(employee, '/expenses')

    cy.contains('tr', description).click()
    cy.contains('button', 'Delete').click() // Cypress accepts the browser confirm dialog
    cy.get('.toast').should('contain', 'Draft deleted.')
    cy.contains('tr', description).should('not.exist')
  })

  it('sees why an expense was rejected and can resubmit it', () => {
    const reason = `Please attach a receipt ${run}`
    cy.fileExpense(employee, { description: `Taxi ${run}` }).then((expense) => {
      cy.decideExpense(manager, expense.id, false, reason)
    })
    cy.openApp(employee, '/overview')

    cy.contains('.mini-row', reason).should('contain', 'rejected').click()
    cy.contains('button', 'Resubmit').click()
    cy.get('.toast').should('contain', 'Expense updated.')
    cy.contains('.mini-row', reason).should('not.exist')
  })

  it("never shows a colleague's expenses", () => {
    const mine = `My own expense ${run}`
    const theirs = `Colleague expense ${run}`
    cy.fileExpense(colleague, { description: theirs })
    cy.fileExpense(employee, { description: mine })
    cy.openApp(employee, '/expenses')

    cy.contains('tr', mine).should('be.visible') // list has loaded
    cy.contains('tr', theirs).should('not.exist')
  })

  it('is refused by the API for manager and admin features', () => {
    cy.apiAs(employee, 'GET', '/expenses/summary').its('status').should('eq', 403)
    cy.apiAs(employee, 'GET', '/admin/users').its('status').should('eq', 403)
    cy.apiAs(employee, 'GET', '/expenses/export').its('status').should('eq', 403)
  })
})
