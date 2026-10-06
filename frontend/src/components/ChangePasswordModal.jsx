import { useState } from 'react'
import { api } from '../api.js'
import { Field, Modal, PasswordInput } from './ui.jsx'

// `required` is true when an admin created or reset the account: the person
// must choose their own password before using the app, so it cannot be closed.
export default function ChangePasswordModal({ required, onClose, onDone }) {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function save(event) {
    event.preventDefault()
    setError('')
    if (form.next !== form.confirm) return setError('The new passwords do not match.')
    setBusy(true)
    try {
      await api('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: form.current, new_password: form.next }),
      })
      onDone('Password changed.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={required ? 'Choose your own password' : 'Change password'} onClose={required ? undefined : onClose}>
      <form onSubmit={save}>
        {required && (
          <p className="auth-subtitle">
            Your account was set up with a temporary password. Choose a new one to continue.
          </p>
        )}
        <Field label={required ? 'Temporary password' : 'Current password'}>
          <PasswordInput
            required
            autoComplete="current-password"
            value={form.current}
            onChange={(e) => setForm({ ...form, current: e.target.value })}
          />
        </Field>
        <Field label="New password (8+ characters)">
          <PasswordInput
            required
            minLength="8"
            autoComplete="new-password"
            value={form.next}
            onChange={(e) => setForm({ ...form, next: e.target.value })}
          />
        </Field>
        <Field label="Repeat new password">
          <PasswordInput
            required
            minLength="8"
            autoComplete="new-password"
            value={form.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
          />
        </Field>
        {error && <div className="form-error">{error}</div>}
        <div className="modal-actions">
          {!required && (
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
          )}
          <button className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save password'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
