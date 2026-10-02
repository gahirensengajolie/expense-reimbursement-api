const BASE = import.meta.env.DEV ? '/api' : ''

const ACCESS_KEY = 'passbook_access'
const REFRESH_KEY = 'passbook_refresh'

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access, refresh) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

// Single request helper: attaches the bearer token, retries once after a
// silent token refresh on 401, and unwraps FastAPI's {"detail": "..."}
// error shape into a plain Error so callers can just read err.message.
export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`

  const response = await fetch(`${BASE}${path}`, { ...options, headers })

  if (response.status === 401 && tokenStore.refresh && !options.skipRefresh) {
    const refreshed = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokenStore.refresh }),
    })
    if (refreshed.ok) {
      const tokens = await refreshed.json()
      tokenStore.set(tokens.access_token, tokens.refresh_token)
      return api(path, { ...options, skipRefresh: true })
    }
    tokenStore.clear()
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Something went wrong. Please try again.')
  }

  return response.status === 204 ? null : response.json()
}
