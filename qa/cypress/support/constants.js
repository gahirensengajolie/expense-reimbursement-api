// Shared by the Node-side tasks and the browser-side commands.
// These must match the environment set in scripts/e2e.sh.

export const ADMIN = {
  email: 'e2e-admin@example.com',
  full_name: 'Administrator',
  initialPassword: 'E2e-Initial-Pass1', // FIRST_ADMIN_PASSWORD: a temporary password
  password: 'E2e-Admin-Pass2', // what the tasks change it to on first use
}

// Admin-created accounts start with this; "normal" seeded users then pick USER_PASSWORD.
export const TEMP_PASSWORD = 'E2e-Temp-Pass1'
export const USER_PASSWORD = 'E2e-Passw0rd!'
