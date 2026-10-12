// The app must stay usable on a phone.
const run = Date.now().toString(36)

describe('Small screens', () => {
  let employee

  before(() => {
    cy.task('seedUser', { full_name: `Pia Phone ${run}`, email: `pia-${run}@example.com` }).then((user) => {
      employee = user
    })
  })

  beforeEach(() => {
    cy.viewport('iphone-x')
  })

  it('keeps the navigation available and working', () => {
    cy.openApp(employee, '/overview')

    cy.contains('nav a', 'Overview').should('be.visible')
    cy.contains('nav a', 'My expenses').should('be.visible').click()
    cy.contains('h1', 'My expenses').should('be.visible')
    cy.contains('button', 'New expense').should('be.visible')
  })

  it('shows the sign-in form without horizontal scrolling', () => {
    cy.visit('/')

    cy.contains('h2', 'Sign in').should('be.visible')
    cy.document().then((doc) => {
      expect(doc.documentElement.scrollWidth, 'page width').to.be.at.most(doc.documentElement.clientWidth)
    })
  })
})
