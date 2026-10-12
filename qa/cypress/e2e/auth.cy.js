// Signing in and out, closed registration, forced password change, disabled accounts.
const run = Date.now().toString(36)

describe('Authentication', () => {
  let employee

  before(() => {
    cy.task('seedUser', { full_name: `Eli Employee ${run}`, email: `eli-${run}@example.com` }).then((user) => {
      employee = user
    })
  })

  it('shows the sign-in form and no "create account" option when sign-up is closed', () => {
    cy.intercept('GET', '/auth/config').as('config')
    cy.visit('/')
    cy.wait('@config').its('response.body.allow_self_registration').should('eq', false)

    cy.contains('h2', 'Sign in').should('be.visible')
    cy.contains('Accounts are created by your administrator').should('be.visible')
    cy.contains('button', 'Create one').should('not.exist')
  })

  it('rejects a wrong password with a clear message', () => {
    cy.signInThroughForm(employee.email, 'Totally-Wrong-1')

    cy.get('.form-error').should('contain', 'Invalid email or password')
    cy.contains('h2', 'Sign in').should('be.visible')
  })

  it('signs in through the form and signs out again', () => {
    cy.signInThroughForm(employee.email, employee.password)

    cy.get('.role-badge').should('have.text', 'Employee')
    cy.contains('nav a', 'My expenses').should('be.visible')

    cy.contains('button', 'Sign out').click()
    cy.contains('h2', 'Sign in').should('be.visible')
    cy.window().its('localStorage').invoke('getItem', 'passbook_access').should('be.null')
  })

  it('makes a newly created person choose their own password before using the app', () => {
    cy.task('seedUser', {
      full_name: `Tia Temp ${run}`,
      email: `tia-${run}@example.com`,
      temporary: true,
    }).then((tia) => {
      cy.signInThroughForm(tia.email, tia.password)

      // The dialog cannot be dismissed.
      cy.contains('.modal-head h2', 'Choose your own password').should('be.visible')
      cy.get('.modal .icon-btn').should('not.exist')

      // Mismatched confirmation is refused.
      cy.field('Temporary password').type(tia.password, { log: false })
      cy.field('New password (8+ characters)').type('Brand-New-Pass9', { log: false })
      cy.field('Repeat new password').type('Different-Pass9', { log: false })
      cy.contains('button', 'Save password').click()
      cy.get('.form-error').should('contain', 'do not match')

      // Correct confirmation lets them in.
      cy.field('Repeat new password').clear().type('Brand-New-Pass9', { log: false })
      cy.contains('button', 'Save password').click()
      cy.contains('.modal-head h2', 'Choose your own password').should('not.exist')
      cy.contains('nav a', 'My expenses').should('be.visible')

      // The temporary password no longer works; the new one does.
      cy.contains('button', 'Sign out').click()
      cy.signInThroughForm(tia.email, tia.password)
      cy.get('.form-error').should('contain', 'Invalid email or password')
      cy.signInThroughForm(tia.email, 'Brand-New-Pass9')
      cy.contains('nav a', 'My expenses').should('be.visible')
    })
  })

  it('does not let a disabled account sign in', () => {
    cy.task('seedUser', { full_name: `Dan Disabled ${run}`, email: `dan-${run}@example.com` }).then((dan) => {
      cy.apiAs('admin', 'PATCH', `/admin/users/${dan.id}`, { is_active: false }).its('status').should('eq', 200)

      cy.signInThroughForm(dan.email, dan.password)
      cy.get('.form-error').should('contain', 'Account is disabled')
    })
  })
})
