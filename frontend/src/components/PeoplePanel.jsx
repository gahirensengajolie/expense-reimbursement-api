import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { initials } from '../format.js'
import { Field, Modal } from './ui.jsx'

// 12 readable characters (no look-alikes) from the browser's secure random source.
function tempPassword() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint8Array(12))
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join('')
}

export default function PeoplePanel({ notify, me }) {
  const [users, setUsers] = useState([])
  const [dialog, setDialog] = useState(null) // { type: 'add' } | { type: 'reset', user }

  function load() {
    api('/admin/users')
      .then(setUsers)
      .catch((err) => notify(err.message))
  }
  useEffect(load, [])

  const managers = users.filter((u) => u.role === 'manager' && u.is_active)

  async function patch(user, changes, message) {
    try {
      await api(`/admin/users/${user.id}`, { method: 'PATCH', body: JSON.stringify(changes) })
      load() // reload: demoting or disabling a manager also unassigns their team
      notify(message)
    } catch (err) {
      notify(err.message)
    }
  }

  return (
    <section className="card" id="people">
      <div className="card-head">
        <div>
          <div className="section-heading">People</div>
          <p className="card-subtitle">
            Add people, set roles and teams. Employees without a manager can be reviewed by any manager.
          </p>
        </div>
        <button className="btn btn-primary btn-compact" onClick={() => setDialog({ type: 'add' })}>
          Add person
        </button>
      </div>

      <div className="people-list">
        {users.map((user) => {
          const isMe = user.id === me.id
          return (
            <div className={`person-row ${user.is_active ? '' : 'person-disabled'}`} key={user.id}>
              <span className="avatar">{initials(user.full_name)}</span>
              <div className="person-copy">
                <strong>
                  {user.full_name} {isMe && <span className="muted">(you)</span>}
                </strong>
                <small>{user.email}</small>
              </div>

              <select
                aria-label={`Role for ${user.full_name}`}
                value={user.role}
                disabled={isMe}
                onChange={(e) => patch(user, { role: e.target.value }, `${user.full_name} is now ${e.target.value}.`)}
              >
                <option value="employee">Employee</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>

              {user.role === 'employee' && (
                <select
                  aria-label={`Manager for ${user.full_name}`}
                  value={user.manager_id ?? ''}
                  onChange={(e) =>
                    patch(user, { manager_id: e.target.value ? Number(e.target.value) : null }, 'Team updated.')
                  }
                >
                  <option value="">No manager</option>
                  {managers.map((m) => (
                    <option key={m.id} value={m.id}>
                      Reports to {m.full_name}
                    </option>
                  ))}
                </select>
              )}

              <span className={`status-dot ${user.is_active ? '' : 'inactive'}`}>
                {user.is_active ? 'Active' : 'Disabled'}
              </span>
              <div className="person-actions">
                <button className="link-btn" onClick={() => setDialog({ type: 'reset', user })}>
                  Reset password
                </button>
                {!isMe && (
                  <button
                    className="link-btn"
                    onClick={() =>
                      patch(
                        user,
                        { is_active: !user.is_active },
                        user.is_active ? `${user.full_name} can no longer sign in.` : `${user.full_name} can sign in again.`
                      )
                    }
                  >
                    {user.is_active ? 'Disable' : 'Enable'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {dialog?.type === 'add' && (
        <AddPersonModal
          managers={managers}
          onClose={() => setDialog(null)}
          onDone={(message) => {
            setDialog(null)
            load()
            notify(message)
          }}
        />
      )}
      {dialog?.type === 'reset' && (
        <ResetPasswordModal
          user={dialog.user}
          onClose={() => setDialog(null)}
          onDone={(message) => {
            setDialog(null)
            notify(message)
          }}
        />
      )}
    </section>
  )
}

function PasswordField({ value, onChange }) {
  return (
    <Field label="Temporary password (they must change it at first sign-in)">
      <div className="inline-field">
        <input required minLength="8" value={value} onChange={(e) => onChange(e.target.value)} />
        <button type="button" className="btn btn-ghost btn-compact" onClick={() => onChange(tempPassword())}>
          Generate
        </button>
      </div>
    </Field>
  )
}

function AddPersonModal({ managers, onClose, onDone }) {
  const [form, setForm] = useState({ full_name: '', email: '', role: 'employee', manager_id: '', password: tempPassword() })
  const [error, setError] = useState('')

  async function save(event) {
    event.preventDefault()
    setError('')
    try {
      await api('/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          manager_id: form.role === 'employee' && form.manager_id ? Number(form.manager_id) : null,
        }),
      })
      onDone(`${form.full_name} added. Share the temporary password with them securely.`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title="Add person" onClose={onClose}>
      <form onSubmit={save}>
        <Field label="Full name">
          <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </Field>
        <Field label="Work email">
          <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Role">
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="employee">Employee: files expenses</option>
            <option value="manager">Manager: approves their team's expenses</option>
            <option value="admin">Admin: pays expenses and manages people</option>
          </select>
        </Field>
        {form.role === 'employee' && (
          <Field label="Manager">
            <select value={form.manager_id} onChange={(e) => setForm({ ...form, manager_id: e.target.value })}>
              <option value="">No manager yet</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <PasswordField value={form.password} onChange={(password) => setForm({ ...form, password })} />
        {error && <div className="form-error">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary">Create account</button>
        </div>
      </form>
    </Modal>
  )
}

function ResetPasswordModal({ user, onClose, onDone }) {
  const [password, setPassword] = useState(tempPassword())
  const [error, setError] = useState('')

  async function save(event) {
    event.preventDefault()
    setError('')
    try {
      await api(`/admin/users/${user.id}/reset-password`, { method: 'POST', body: JSON.stringify({ password }) })
      onDone(`Password reset for ${user.full_name}. Share the temporary password securely.`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title={`Reset password: ${user.full_name}`} onClose={onClose}>
      <form onSubmit={save}>
        <PasswordField value={password} onChange={setPassword} />
        {error && <div className="form-error">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary">Set temporary password</button>
        </div>
      </form>
    </Modal>
  )
}
