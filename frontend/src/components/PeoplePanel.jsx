import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { initials } from '../format.js'

export default function PeoplePanel({ notify }) {
  const [users, setUsers] = useState([])

  useEffect(() => {
    api('/admin/users')
      .then(setUsers)
      .catch((err) => notify(err.message))
  }, [])

  async function updateRole(user, role) {
    try {
      await api(`/admin/users/${user.id}/role`, { method: 'PATCH', body: JSON.stringify({ role }) })
      setUsers((items) => items.map((item) => (item.id === user.id ? { ...item, role } : item)))
      notify(`${user.full_name}'s role is now ${role}.`)
    } catch (err) {
      notify(err.message)
    }
  }

  return (
    <section className="card" id="people">
      <div className="card-head">
        <div>
          <div className="section-heading">People</div>
          <p className="card-subtitle">Manage who can review and reimburse expenses.</p>
        </div>
        <span className="muted">{users.length} members</span>
      </div>

      <div className="people-list">
        {users.map((user) => (
          <div className="person-row" key={user.id}>
            <span className="avatar">{initials(user.full_name)}</span>
            <div className="person-copy">
              <strong>{user.full_name}</strong>
              <small>{user.email}</small>
            </div>
            <select value={user.role} onChange={(e) => updateRole(user, e.target.value)}>
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
            <span className={`status-dot ${user.is_active ? '' : 'inactive'}`}>
              {user.is_active ? 'Active' : 'Disabled'}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
