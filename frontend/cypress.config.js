import { defineConfig } from 'cypress'
import { registerTasks } from './cypress/support/tasks.js'

export default defineConfig({
  e2e: {
    // scripts/e2e.sh starts the real app (API + built frontend) on this port.
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://127.0.0.1:8010',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',
    viewportWidth: 1280,
    viewportHeight: 800,
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 8000,
    retries: { runMode: 1, openMode: 0 },
    setupNodeEvents(on, config) {
      registerTasks(on, config.baseUrl)
      return config
    },
  },
})
