// What an administrator sees and can do: paying expenses and managing people.
const run = Date.now().toString(36)

describe('Admin', () => {
  let admin
  let manager
  let employee
  const approvedText = `Approved flight ${run}`

  before(() => {
    cy.task('adminAccount')
      .then((account) => {
        admin = account
        return cy.task('seedUser', { full_name: `Ada Manager ${run}`, email: `ada-${run}@example.com`, role: 'manager' })
      })
      .then((user) => {
        manager = user
        return cy.task('seedUser', {
          full_name: `Ned Employee ${run}`,
          email: `ned-${run}@example.com`,
          manager_id: manager.id,
        })
      })
      .then((user) => {
        employee = user
        return cy.fileExpense(employee, { category: 'travel', amount: 320, description: approvedText })
      })
      .then((expense) => cy.decideExpense(manager, expense.id, true, 'Approved'))
  })

  it('gets every section of the admin navigation', () => {
    cy.openApp(admin, '/')

    cy.get('.role-badge').should('have.text', 'Admin')
    cy.get('nav').within(() => {
      ;['Spending dashboard', 'Approval queue', 'Payments', 'All expenses', 'People & roles'].forEach((label) =>
        cy.contains('a', label).should('be.visible')
      )
      cy.contains('a', 'My expenses').should('not.exist')
    })
    cy.contains('button', 'New expense').should('not.exist')
  })

  it('shows the business-wide dashboard', () => {
    cy.openApp(admin, '/dashboard')

    cy.contains('h1', 'Spending dashboard').should('be.visible')
    cy.contains('.metric-label', 'Total spend').should('be.visible')
    cy.contains('.section-heading', 'Spend by month').should('be.visible')
  })

  it('marks an approved expense as reimbursed', () => {
    cy.openApp(admin, '/payments')

    cy.contains('.queue-row', approvedText).should('contain', employee.full_name)
    cy.contains('.queue-row', approvedText).contains('button', 'Mark reimbursed').click()
    cy.get('.toast').should('contain', 'as reimbursed')
    cy.contains('.queue-row', approvedText).should('not.exist')

    cy.contains('nav a', 'All expenses').click()
    cy.contains('tr', approvedText).should('contain', 'reimbursed')
  })

  describe('People & roles', () => {
    it('adds a person with a manager', () => {
      const name = `Hana Hire ${run}`
      cy.openApp(admin, '/people')

      cy.contains('button', 'Add person').click()
      cy.contains('.modal-head h2', 'Add person').should('be.visible')
      cy.field('Full name').type(name)
      cy.field('Work email').type(`hana-${run}@example.com`)
      cy.field('Manager').select(manager.full_name)
      cy.contains('button', 'Create account').click()

      cy.get('.toast').should('contain', 'added')
      cy.contains('.person-row', name).should('contain', `hana-${run}@example.com`)
      cy.get(`select[aria-label="Manager for ${name}"]`).should('contain', manager.full_name)
    })

    it('refuses to add someone with an email that is already in use', () => {
      cy.openApp(admin, '/people')

      cy.contains('button', 'Add person').click()
      cy.field('Full name').type('Duplicate Person')
      cy.field('Work email').type(employee.email)
      cy.contains('button', 'Create account').click()

      cy.get('.form-error').should('contain', 'Email already registered')
    })

    it('assigns an employee to a manager', () => {
      cy.task('seedUser', { full_name: `Uma Unassigned ${run}`, email: `uma-${run}@example.com` }).then((uma) => {
        cy.openApp(admin, '/people')

        cy.get(`select[aria-label="Manager for ${uma.full_name}"]`).select(`Reports to ${manager.full_name}`)
        cy.get('.toast').should('contain', 'Team updated.')
        cy.apiAs('admin', 'GET', '/admin/users').then(({ data }) => {
          expect(data.find((user) => user.id === uma.id).manager_id).to.eq(manager.id)
        })
      })
    })

    it('disables and re-enables an account', () => {
      cy.task('seedUser', { full_name: `Dee Disable ${run}`, email: `dee-${run}@example.com` }).then((dee) => {
        cy.openApp(admin, '/people')

        cy.contains('.person-row', dee.full_name).contains('button', 'Disable').click()
        cy.get('.toast').should('contain', 'can no longer sign in')
        cy.contains('.person-row', dee.full_name).should('contain', 'Disabled')

        cy.contains('.person-row', dee.full_name).contains('button', 'Enable').click()
        cy.get('.toast').should('contain', 'can sign in again')
        cy.contains('.person-row', dee.full_name).should('contain', 'Active')
      })
    })

    it('resets a forgotten password to a temporary one', () => {
      cy.task('seedUser', { full_name: `Rex Reset ${run}`, email: `rex-${run}@example.com` }).then((rex) => {
        cy.openApp(admin, '/people')

        cy.contains('.person-row', rex.full_name).contains('button', 'Reset password').click()
        cy.contains('.modal-head h2', `Reset password: ${rex.full_name}`).should('be.visible')
        cy.get('.modal input')
          .invoke('val')
          .then((temporary) => {
            expect(temporary).to.have.length.of.at.least(8)
            cy.contains('button', 'Set temporary password').click()
            cy.get('.toast').should('contain', `Password reset for ${rex.full_name}`)

            cy.request({ method: 'POST', url: '/auth/login', body: { email: rex.email, password: rex.password }, failOnStatusCode: false })
              .its('status')
              .should('eq', 401)
            cy.request('POST', '/auth/login', { email: rex.email, password: temporary }).its('status').should('eq', 200)
          })
      })
    })

    it('does not let admins change their own role or disable themselves', () => {
      cy.openApp(admin, '/people')

      cy.contains('.person-row', '(you)').within(() => {
        cy.get('select').first().should('be.disabled')
        cy.contains('button', 'Disable').should('not.exist')
      })
    })
  })
})
