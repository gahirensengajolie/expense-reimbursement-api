import { useState } from 'react'
import { api, tokenStore } from '../api.js'
import { Field } from '../components/ui.jsx'

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'register') {
        await api('/auth/register', { method: 'POST', body: JSON.stringify(form), skipRefresh: true })
      }
      const tokens = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: form.email, password: form.password }),
        skipRefresh: true,
      })
      tokenStore.set(tokens.access_token, tokens.refresh_token)
      onAuthenticated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <section className="auth-intro">
        <div className="wordmark">Passbook</div>
        <h1>A clear record of every expense, from request to reimbursement.</h1>
        <p>
          One shared ledger for what was spent, who approved it, and when it was paid back —
          nothing gets lost between a receipt and a reimbursement.
        </p>
      </section>
      <section className="auth-panel">
        <form className="auth-form" onSubmit={submit}>
          <h2>{mode === 'login' ? 'Sign in' : 'Create your account'}</h2>
          <p className="auth-subtitle">
            {mode === 'login'
              ? 'Enter your work email and password.'
              : 'New accounts start as employees; an admin can change your role later.'}
          </p>

          {mode === 'register' && (
            <Field label="Full name">
              <input
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Alex Morgan"
              />
            </Field>
          )}

          <Field label="Work email">
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@company.com"
            />
          </Field>

          <Field label="Password">
            <input
              required
              minLength="8"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="At least 8 characters"
            />
          </Field>

          {error && <div className="form-error">{error}</div>}

          <button className="btn btn-primary btn-full" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>

          <div className="auth-switch">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              className="link-btn"
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login')
                setError('')
              }}
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
