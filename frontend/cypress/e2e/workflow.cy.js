// The whole journey of one expense, using the real screens for each role.
const run = Date.now().toString(36)

describe('Expense workflow across roles', () => {
  let admin
  let manager
  let employee

  before(() => {
    cy.task('adminAccount')
      .then((account) => {
        admin = account
        return cy.task('seedUser', { full_name: `Wes Manager ${run}`, email: `wes-${run}@example.com`, role: 'manager' })
      })
      .then((user) => {
        manager = user
        return cy.task('seedUser', {
          full_name: `Wendy Employee ${run}`,
          email: `wendy-${run}@example.com`,
          manager_id: manager.id,
        })
      })
      .then((user) => {
        employee = user
      })
  })

  it('goes from a draft to reimbursed, and the employee can follow every step', () => {
    const description = `Conference ticket ${run}`

    // 1. The employee files it and submits it.
    cy.openApp(employee, '/overview')
    cy.contains('button', 'New expense').click()
    cy.field('Category').select('training')
    cy.field('Amount (USD)').type('300')
    cy.field('What was this for?').type(description)
    cy.contains('button', 'Create draft').click()
    cy.get('.toast').should('contain', 'Draft created.')
    cy.contains('nav a', 'My expenses').click()
    cy.contains('tr', description).click()
    cy.contains('button', 'Submit for review').click()
    cy.get('.toast').should('contain', 'Expense updated.')

    // 2. Their manager approves it from the queue.
    cy.openApp(manager, '/queue')
    cy.answerPromptWith('Approved in the e2e workflow')
    cy.contains('.queue-row', description).should('contain', employee.full_name)
    cy.contains('.queue-row', description).contains('button', 'Approve').click()
    cy.get('.toast').should('contain', 'Expense approved.')

    // 3. The admin pays it.
    cy.openApp(admin, '/payments')
    cy.contains('.queue-row', description).contains('button', 'Mark reimbursed').click()
    cy.get('.toast').should('contain', 'as reimbursed')

    // 4. The employee sees it as reimbursed, with the full history.
    cy.openApp(employee, '/expenses')
    cy.contains('tr', description).should('contain', 'reimbursed').click()
    cy.get('.timeline').should('contain', 'submitted').and('contain', 'approved').and('contain', 'reimbursed')
  })

  it('lets the employee fix and resubmit a rejected expense until it is approved', () => {
    const description = `Software licence ${run}`
    cy.fileExpense(employee, { category: 'software', amount: 120, description }).then((expense) => {
      cy.decideExpense(manager, expense.id, false, `Wrong cost centre ${run}`)

      cy.openApp(employee, '/overview')
      cy.contains('.mini-row', `Wrong cost centre ${run}`).click()
      cy.contains('button', 'Resubmit').click()
      cy.get('.toast').should('contain', 'Expense updated.')

      cy.openApp(manager, '/queue')
      cy.contains('.queue-row', description).should('exist')
    })
  })
})
