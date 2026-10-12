// Node-side helpers: they talk to the API directly to ARRANGE test data fast
// (create people, file expenses, ...). The tests then use the real screens to
// ACT and ASSERT. Called from specs with cy.task(name, args).

import { ADMIN, TEMP_PASSWORD, USER_PASSWORD } from './constants.js'

export function registerTasks(on, baseUrl) {
  async function call(method, path, { token, body } = {}) {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const text = await response.text()
    let data = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = text
    }
    return { status: response.status, data }
  }

  async function login(email, password) {
    const result = await call('POST', '/auth/login', { body: { email, password } })
    if (result.status !== 200) {
      throw new Error(`Sign-in failed for ${email}: ${result.status} ${JSON.stringify(result.data)}`)
    }
    return result.data.access_token
  }

  // The first admin is created from FIRST_ADMIN_* with a temporary password
  // that must be changed. Do that once, then use the final password.
  async function adminToken() {
    const final = await call('POST', '/auth/login', {
      body: { email: ADMIN.email, password: ADMIN.password },
    })
    if (final.status === 200) return final.data.access_token

    const token = await login(ADMIN.email, ADMIN.initialPassword)
    const changed = await call('POST', '/auth/change-password', {
      token,
      body: { current_password: ADMIN.initialPassword, new_password: ADMIN.password },
    })
    if (changed.status !== 200) {
      throw new Error(`Could not set the e2e admin password: ${changed.status} ${JSON.stringify(changed.data)}`)
    }
    return login(ADMIN.email, ADMIN.password)
  }

  async function tokenFor(as) {
    return as === 'admin' ? adminToken() : login(as.email, as.password)
  }

  on('task', {
    // { email, password, full_name } of the admin, ready to sign in with.
    async adminAccount() {
      await adminToken()
      return { email: ADMIN.email, password: ADMIN.password, full_name: ADMIN.full_name }
    },

    // Create an account the way an admin would. By default the person has
    // already chosen their own password; pass temporary: true to leave the
    // "must change password" step for the test to do.
    async seedUser({ email, full_name, role = 'employee', manager_id = null, temporary = false }) {
      const token = await adminToken()
      const created = await call('POST', '/admin/users', {
        token,
        body: { email, full_name, role, manager_id, password: TEMP_PASSWORD },
      })
      if (created.status !== 201) {
        throw new Error(`Could not create ${email}: ${created.status} ${JSON.stringify(created.data)}`)
      }
      const user = { id: created.data.id, email, full_name, role, password: TEMP_PASSWORD }
      if (temporary) return user

      const own = await login(email, TEMP_PASSWORD)
      const changed = await call('POST', '/auth/change-password', {
        token: own,
        body: { current_password: TEMP_PASSWORD, new_password: USER_PASSWORD },
      })
      if (changed.status !== 200) {
        throw new Error(`Could not finish setting up ${email}: ${changed.status} ${JSON.stringify(changed.data)}`)
      }
      return { ...user, password: USER_PASSWORD }
    },

    // Any API call as 'admin' or as { email, password }. Never throws on HTTP
    // errors so tests can assert 403/404 etc.: returns { status, data }.
    async api({ method = 'GET', path, as, body }) {
      return call(method, path, { token: await tokenFor(as), body })
    },
  })
}
